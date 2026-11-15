"""Verify CSV downloads against filtered invented records, without network calls."""

from html import unescape
from io import StringIO
import re
from urllib.parse import parse_qs, urlsplit

import pandas as pd
import pytest

import app as web


@pytest.fixture
def records(monkeypatch):
    data = pd.DataFrame({
        "id": ["1", "2", "3", "4"],
        "dateadded": ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-03"],
        "country": ["US", "US", "DE", "US"],
        "threat": ["category_a", "category_a", "category_a", "category_b"],
        "tags": ["mirai,elf", "elf", "mirai", "mirai"],
        "url_status": ["offline", "online", "offline", "offline"],
    })
    monkeypatch.setattr(web, "load_filtered_data", lambda: data)
    return data


@pytest.mark.parametrize("name", [
    "by_country", "by_threat", "by_tag", "daily_additions", "status_summary"
])
def test_download_contents_use_all_applied_filters(records, name):
    original = records.copy(deep=True)
    response = web.app.test_client().get(f"/results/download/{name}", query_string={
        "country": "US", "threat": "category_a", "tag": "mirai", "status": "offline"
    })
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert f"attachment; filename=urlhaus-{name}.csv" == response.headers["Content-Disposition"]
    summary = pd.read_csv(StringIO(response.get_data(as_text=True)))
    assert not any(column.startswith("Unnamed:") for column in summary)
    if name == "status_summary":
        assert summary.iloc[0]["total"] == 1
        assert summary.iloc[0]["offline_percentage"] == 100
    elif name == "by_tag":
        assert dict(summary.values) == {"elf": 1, "mirai": 1}
    else:
        assert summary["url_count"].tolist() == [1]
        if name == "by_country":
            assert summary["country"].tolist() == ["US"]
        if name == "by_threat":
            assert summary["threat"].tolist() == ["category_a"]
        if name == "daily_additions":
            assert summary["date"].iloc[0].startswith("2026-11-01")
    pd.testing.assert_frame_equal(records, original)


def test_download_links_preserve_multiple_tags_and_filters(records):
    html = web.app.test_client().get("/results", query_string={
        "country": "US", "threat": "category_a", "tag": ["mirai", "elf"], "status": "offline"
    }).get_data(as_text=True)
    links = re.findall(r'href="(/results/download/[^\"]+)"', html)
    assert len(links) == 5
    for link in links:
        query = parse_qs(urlsplit(unescape(link)).query)
        assert query == {"country": ["US"], "threat": ["category_a"],
                         "tag": ["elf", "mirai"], "status": ["offline"]}


def test_download_without_matches_or_unknown_summary(records):
    client = web.app.test_client()
    assert client.get("/results/download/by_country?country=ZZ").status_code == 400
    assert client.get("/results/download/not_a_summary").status_code == 404


def test_download_without_saved_data(monkeypatch):
    def missing():
        raise FileNotFoundError
    monkeypatch.setattr(web, "load_filtered_data", missing)
    assert web.app.test_client().get("/results/download/by_country").status_code == 404


def test_download_with_empty_selection(monkeypatch):
    monkeypatch.setattr(web, "load_filtered_data", lambda: pd.DataFrame())
    assert web.app.test_client().get("/results/download/by_country").status_code == 400


def test_unknown_status_percentage_downloads_as_blank(monkeypatch):
    monkeypatch.setattr(web, "load_filtered_data", lambda: pd.DataFrame({
        "dateadded": ["2026-11-01"], "url_status": [None]
    }))
    response = web.app.test_client().get("/results/download/status_summary")
    summary = pd.read_csv(StringIO(response.get_data(as_text=True)))
    assert summary.iloc[0]["unknown"] == 1
    assert pd.isna(summary.iloc[0]["offline_percentage"])
