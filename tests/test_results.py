"""Results page states using local invented data, never the URLhaus API."""

import pandas as pd

import app as web


def test_results_without_saved_data(monkeypatch):
    def missing_data():
        raise FileNotFoundError
    monkeypatch.setattr(web, "load_filtered_data", missing_data)
    response = web.app.test_client().get("/results")
    assert response.status_code == 200
    assert b"Fetch data first" in response.data
    assert b'Summary statistics' not in response.data


def test_results_with_empty_selection(monkeypatch):
    monkeypatch.setattr(web, "load_filtered_data", lambda: pd.DataFrame())
    response = web.app.test_client().get("/results")
    assert response.status_code == 200
    assert b"Your saved selection is empty" in response.data


def test_results_layout_with_saved_records(monkeypatch):
    monkeypatch.setattr(web, "load_filtered_data", lambda: pd.DataFrame({
        "id": ["1", "2"], "dateadded": ["2026-11-01"] * 2,
        "url_status": ["online", "offline"],
    }))
    response = web.app.test_client().get("/results")
    assert response.status_code == 200
    assert b"<strong>2</strong> records" in response.data
    assert b"Summary statistics" in response.data
    assert b"Daily additions" in response.data
    assert b"Hosting countries" in response.data
    assert b"IP Geolocation by DB-IP" in response.data
    assert b"50.0%" in response.data


def test_results_summary_excludes_duplicates_and_unknown_status(monkeypatch):
    records = pd.DataFrame({
        "id": ["1", "1", "2", "3", "4"],
        "dateadded": ["2026-11-01"] * 5,
        "url_status": ["online", "online", "offline", "offline", None],
    })
    monkeypatch.setattr(web, "load_filtered_data", lambda: records)
    html = web.app.test_client().get("/results").get_data(as_text=True)
    assert "<strong>4</strong> records" in html
    assert "66.7%" in html
    for label, count in [("Total records", 4), ("Online", 1), ("Offline", 2), ("Unknown status", 1)]:
        assert f"<dt>{label}</dt>\n                <dd>{count}</dd>" in html
    assert len(records) == 5


def test_results_summary_without_known_status_shows_unavailable(monkeypatch):
    monkeypatch.setattr(web, "load_filtered_data", lambda: pd.DataFrame({
        "dateadded": ["2026-11-01"], "url_status": [None],
    }))
    html = web.app.test_client().get("/results").get_data(as_text=True)
    assert "<dd>N/A</dd>" in html
    assert "No records have a known online/offline status." in html
