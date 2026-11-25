"""Fetch to Results integration with temporary storage and no live downloads."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

import app as web
import backend.data_pipeline as pipeline
import backend.data_storage as storage


def test_fetch_saves_selection_and_results_displays_it(monkeypatch, tmp_path):
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=2)).isoformat()
    end = today.isoformat()
    rows = pd.DataFrame({
        "id": ["1", "2", "3"],
        "dateadded": pd.to_datetime([end, end, end], utc=True),
        "last_online": pd.to_datetime([end, end, end], utc=True),
        "url": ["https://example.invalid/a", "https://other.invalid/b", "https://example.invalid/c"],
        "defanged_url": ["hxxps://example[.]invalid/a", "hxxps://other[.]invalid/b", "hxxps://example[.]invalid/c"],
        "url_status": ["online", "offline", "offline"],
        "threat": ["malware_download"] * 3,
        "tags": ["zip,other", "zip", "elf"],
        "hostname": ["example.invalid", "other.invalid", "example.invalid"],
        "country": ["US", "DE", "US"],
    })
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "DATA_DIR", tmp_path)
    monkeypatch.setattr(web, "get_cleaned_data", lambda: rows)
    client = web.app.test_client()
    response = client.post("/fetch", data={
        "start_date": start, "end_date": end, "threat": "malware_download",
        "tag": "zip", "q": "example.invalid",
    })
    assert response.status_code == 200
    saved = storage.load_filtered_data()
    assert saved["id"].tolist() == ["1"]
    assert saved.attrs["fetch_metadata"]["selection"] == {
        "start_date": start, "end_date": end, "threat": "malware_download",
        "tag": "zip", "query": "example.invalid",
    }
    html = client.get("/results").get_data(as_text=True)
    assert "Fetch selection" in html and "example.invalid" in html
    assert "zip" in html and start in html and end in html
    assert 'name="threat"' not in html and 'name="tag"' not in html
    assert 'value="tag"' in html  # Grouping remains available.
    assert "Showing 1 records" in html
    preview = client.get("/fetch?saved=1").get_data(as_text=True)
    assert "Back to search" in preview
    assert "tag=zip" in preview and "q=example.invalid" in preview


def test_invalid_fetch_dates_do_not_trigger_download(monkeypatch):
    def unexpected():
        pytest.fail("Invalid input must not download data")
    monkeypatch.setattr(web, "get_cleaned_data", unexpected)
    html = web.app.test_client().post("/fetch", data={
        "start_date": "bad", "end_date": "bad",
    }).get_data(as_text=True)
    assert "Enter a valid start date and end date" in html


@pytest.mark.parametrize("error", [ValueError("missing column"), pd.errors.EmptyDataError("empty")])
def test_unreadable_csv_has_useful_page_and_download_errors(monkeypatch, error):
    def unreadable():
        raise error
    monkeypatch.setattr(web, "load_filtered_data", unreadable)
    client = web.app.test_client()
    response = client.get("/results")
    assert response.status_code == 200
    assert "Saved data needs attention" in response.get_data(as_text=True)
    assert client.get("/results/download/by_country").status_code == 400


def test_missing_analysis_columns_do_not_crash_results(monkeypatch):
    monkeypatch.setattr(web, "load_filtered_data", lambda: pd.DataFrame({"id": ["1"]}))
    client = web.app.test_client()
    assert b"Saved data needs attention" in client.get("/results").data
    assert client.get("/results/download/by_country").status_code == 400


def test_changed_dataset_prevents_stale_download_and_save(monkeypatch, tmp_path):
    records = pd.DataFrame({"dateadded": ["2026-11-01"], "url_status": ["online"]})
    records.attrs["snapshot_id"] = "new-snapshot"
    monkeypatch.setattr(web, "load_filtered_data", lambda: records)
    directory = tmp_path / "summaries"
    monkeypatch.setitem(web.app.config, "SUMMARY_OUTPUT_DIR", directory)
    client = web.app.test_client()
    assert client.get("/results/download/by_country?snapshot=old-snapshot").status_code == 409
    html = client.post("/results?snapshot=old-snapshot").get_data(as_text=True)
    assert "The Fetch dataset changed" in html
    assert not directory.exists()
    assert client.get("/results/download/by_country?snapshot=new-snapshot").status_code == 200
