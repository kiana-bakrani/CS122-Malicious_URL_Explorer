"""Exercise the explicit local-save action with temporary files."""

import pandas as pd
import pytest

import app as web


@pytest.fixture
def selection(monkeypatch, tmp_path):
    records = pd.DataFrame({
        "id": ["1", "2", "3", "4"],
        "dateadded": ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-03"],
        "country": ["US", "US", "DE", "US"],
        "threat": ["a", "a", "a", "b"],
        "tags": ["mirai,elf", "elf", "mirai", "mirai"],
        "url_status": ["offline", "online", "offline", "offline"],
    })
    monkeypatch.setattr(web, "load_filtered_data", lambda: records)
    monkeypatch.setitem(web.app.config, "SUMMARY_OUTPUT_DIR", tmp_path / "summaries")
    return records, tmp_path / "summaries"


def test_save_uses_applied_filters_and_preserves_source(selection):
    source, directory = selection
    original = source.copy(deep=True)
    client = web.app.test_client()
    query = {"country": "US", "status": "offline", "group_by": "tag"}
    client.get("/results", query_string=query)
    assert not directory.exists()  # Viewing Results never writes summaries.
    response = client.post("/results", query_string=query)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Saved 5 summary CSV files" in html
    assert len(list(directory.glob("*.csv"))) == 5
    assert pd.read_csv(directory / "by_country.csv").to_dict("records") == [
        {"country": "US", "url_count": 2}
    ]
    assert dict(pd.read_csv(directory / "by_tag.csv").values) == {"mirai": 2, "elf": 1}
    assert pd.read_csv(directory / "status_summary.csv").iloc[0]["offline_percentage"] == 100
    assert 'value="tag" selected' in html
    assert 'value="US" selected' in html
    pd.testing.assert_frame_equal(source, original)
    # A later save replaces prior results rather than appending them.
    client.post("/results", query_string={"country": "DE"})
    assert pd.read_csv(directory / "by_country.csv").iloc[0]["country"] == "DE"


def test_empty_filter_does_not_replace_existing_summaries(selection):
    _, directory = selection
    client = web.app.test_client()
    client.post("/results")
    before = {p.name: p.read_bytes() for p in directory.glob("*.csv")}
    html = client.post("/results?country=ZZ").get_data(as_text=True)
    assert "No records match these filters" in html
    assert "Saved 5" not in html
    assert before == {p.name: p.read_bytes() for p in directory.glob("*.csv")}


def test_save_error_keeps_results_visible(selection, monkeypatch):
    def failed_save(*args):
        raise PermissionError("not writable")
    monkeypatch.setattr(web, "save_summary_csvs", failed_save)
    html = web.app.test_client().post("/results").get_data(as_text=True)
    assert "Could not save all summary files" in html
    assert "Saved 5" not in html
    assert "Summary statistics" in html


def test_missing_dataset_cannot_save(monkeypatch, tmp_path):
    def missing():
        raise FileNotFoundError
    monkeypatch.setattr(web, "load_filtered_data", missing)
    monkeypatch.setitem(web.app.config, "SUMMARY_OUTPUT_DIR", tmp_path / "summaries")
    html = web.app.test_client().post("/results").get_data(as_text=True)
    assert "Fetch data first" in html
    assert not (tmp_path / "summaries").exists()
