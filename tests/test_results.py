"""Results page states using local invented data, never the URLhaus API."""

import pandas as pd
import pytest
import base64
import re

import app as web


@pytest.mark.parametrize("view", ["timeseries", "map"])
def test_selected_chart_uses_the_same_filtered_records_as_statistics(monkeypatch, view):
    records = pd.DataFrame({
        "id": ["1", "2", "3"],
        "dateadded": ["2026-11-01", "2026-11-02", "2026-11-03"],
        "country": ["US", "US", "DE"],
        "threat": ["malware_download"] * 3,
        "tags": ["mirai", "elf", "mirai"],
        "url_status": ["offline", "online", "offline"],
    })
    monkeypatch.setattr(web, "load_filtered_data", lambda: records)
    name = "create_country_map" if view == "map" else "create_timeseries_chart"
    original_builder = getattr(web, name)
    received = []

    def capture_selection(selection):
        received.extend(selection["id"].tolist())
        return original_builder(selection)

    monkeypatch.setattr(web, name, capture_selection)
    html = web.app.test_client().get("/results", query_string={
        "view": view, "country": "US", "tag": "mirai", "status": "offline"
    }).get_data(as_text=True)
    assert received == ["1"]
    assert "Showing 1 records" in html
    assert f'value="{view}" checked' in html
    assert 'value="mirai" checked' in html
    encoded = re.search(r'src="data:image/png;base64,([^"]+)"', html).group(1)
    assert base64.b64decode(encoded).startswith(b"\x89PNG\r\n\x1a\n")
    # Download the existing image, so data changes cannot alter the saved chart.
    download = re.search(
        r'href="data:image/png;base64,([^"]+)"\s+download="([^"]+)"', html
    )
    assert download is not None
    assert download.group(1) == encoded
    assert download.group(2) == f"urlhaus-{view}.png"
    assert "connected in a later section" not in html


def test_empty_filter_selection_does_not_render_chart(monkeypatch):
    monkeypatch.setattr(web, "load_filtered_data", lambda: pd.DataFrame({
        "dateadded": ["2026-11-01"], "url_status": ["online"], "country": ["US"],
    }))
    html = web.app.test_client().get("/results?country=DE&view=map").get_data(as_text=True)
    assert "No records match these filters" in html
    assert "data:image/png" not in html
    assert "Save Plot" not in html
    assert 'value="map" checked' in html


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


@pytest.mark.parametrize("country, count, percentage", [
    ("all", 4, "66.7%"), ("US", 2, "50.0%"),
    ("DE", 1, "100.0%"), ("Unknown", 1, "<dd>N/A</dd>"),
])
def test_country_filter_updates_statistics_without_changing_saved_data(monkeypatch, country, count, percentage):
    records = pd.DataFrame({
        "id": ["1", "2", "3", "4"],
        "dateadded": ["2026-11-01"] * 4,
        "country": ["US", "US", "DE", None],
        "url_status": ["online", "offline", "offline", None],
    })
    original = records.copy(deep=True)
    monkeypatch.setattr(web, "load_filtered_data", lambda: records)
    response = web.app.test_client().get("/results", query_string={"country": country})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert f"Showing {count} records" in html
    assert percentage in html
    for code in ["US", "DE", "Unknown"]:
        assert f'value="{code}"' in html
    assert f'value="{country}" selected' in html
    pd.testing.assert_frame_equal(records, original)


def test_country_without_matches_keeps_dropdown_and_reset(monkeypatch):
    monkeypatch.setattr(web, "load_filtered_data", lambda: pd.DataFrame({
        "dateadded": ["2026-11-01"], "country": ["US"], "url_status": ["online"],
    }))
    html = web.app.test_client().get("/results?country=ZZ").get_data(as_text=True)
    assert "No records match these filters" in html
    assert 'value="US"' in html
    assert 'href="/results">Reset' in html
    assert "Your saved selection is empty" not in html
    assert "Summary statistics" not in html


@pytest.mark.parametrize("query, expected_count", [
    ({"threat": "category_a"}, 3),
    ({"status": "offline"}, 2),
    ({"status": "unknown"}, 1),
    ({"tag": "mirai"}, 2),
    ({"tag": ["mirai", "elf"]}, 3),
    ({"country": "US", "threat": "category_a", "tag": "mirai", "status": "offline"}, 1),
    ({"tag": "mir"}, 0),
    ({"country": "DE", "status": "online"}, 0),
    ({"status": "unavailable"}, 0),
])
def test_results_filters_combine_and_match_complete_tags(monkeypatch, query, expected_count):
    records = pd.DataFrame({
        "id": ["1", "2", "3", "4"],
        "dateadded": ["2026-11-01"] * 4,
        "country": ["US", "US", "DE", "DE"],
        "threat": ["category_a", "category_a", "category_b", "category_a"],
        "tags": ["Mirai, elf", " mirai ", "elf", None],
        "url_status": ["online", "offline", "offline", None],
    })
    original = records.copy(deep=True)
    monkeypatch.setattr(web, "load_filtered_data", lambda: records)
    client = web.app.test_client()
    response = client.get("/results", query_string=query)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    if expected_count:
        assert f"Showing {expected_count} records" in html
    else:
        assert "No records match these filters" in html
    assert 'value="category_b"' in html  # Options remain available after filtering.
    for tag in query.get("tag", []) if isinstance(query.get("tag"), list) else [query.get("tag")]:
        if tag:
            assert f'value="{tag}" checked' in html
    assert "Showing 4 records" in client.get("/results").get_data(as_text=True)
    pd.testing.assert_frame_equal(records, original)
