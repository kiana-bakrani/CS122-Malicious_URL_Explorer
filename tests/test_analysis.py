"""Check analysis results using invented metadata, without network access."""

import pandas as pd
import pytest

from data_visualization.analysis import (
    prepare_records, count_by_category, count_by_tag,
    count_daily_additions, count_daily_totals, calculate_daily_trend, summarize_status,
)


def test_summaries_handle_duplicates_missing_fields_and_overlapping_tags():
    source = pd.DataFrame({
        "id": ["1", "1", "2", None, None],
        "dateadded": ["2026-11-01", "2026-11-01", "2026-11-03", "bad", None],
        "threat": ["malware_download"] * 5,
        "tags": ["Mirai, mirai, elf", "Mirai", "elf", None, ""],
        "url_status": [" ONLINE ", "online", "offline", None, "unrecognized"],
    })
    records = prepare_records(source)
    assert len(source) == 5  # The original data has not been changed.
    assert len(records) == 4
    assert count_by_category(records, "country").to_dict("records") == [
        {"country": "Unknown", "url_count": 4}
    ]
    assert dict(count_by_tag(records).values) == {"elf": 2, "mirai": 1}
    daily = count_daily_additions(records)
    assert daily["url_count"].tolist() == [1, 0, 1]
    assert str(daily["date"].dt.tz) == "UTC"
    assert summarize_status(records) == {
        "total": 4, "online": 1, "offline": 1, "unknown": 2,
        "offline_percentage": 50.0,
    }


@pytest.mark.parametrize("empty", [False, True])
def test_no_known_status_or_valid_dates_does_not_claim_zero_percent(empty):
    source = pd.DataFrame({"dateadded": [None], "url_status": [None]})
    if empty:
        source = source.iloc[:0]
    records = prepare_records(source)
    assert summarize_status(records)["offline_percentage"] is None
    assert count_daily_additions(records).empty
    assert count_by_tag(records).empty


def test_daily_totals_combine_threats_and_normalize_dates_to_utc():
    source = pd.DataFrame({
        "dateadded": [
            "2026-11-01T12:00:00+00:00",
            "2026-11-01T13:00:00+00:00",
            "2026-11-02T23:30:00-08:00",
        ],
        "threat": ["category_a", "category_b", "category_a"],
        "url_status": ["online"] * 3,
    })
    daily = count_daily_totals(prepare_records(source))
    assert daily["url_count"].tolist() == [2, 0, 1]
    assert daily["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-11-01", "2026-11-02", "2026-11-03"
    ]
    assert daily["url_count"].sum() == len(source)


def test_daily_totals_handle_no_valid_dates():
    records = prepare_records(pd.DataFrame({
        "dateadded": [None], "url_status": ["unknown"]
    }))
    for selection in [records, records.iloc[:0]]:
        daily = count_daily_totals(selection)
        assert daily.empty
        assert daily.columns.tolist() == ["date", "url_count"]


@pytest.mark.parametrize("counts, expected_slope", [
    ([1, 3, 5], 2), ([5, 3, 1], -2), ([2, 2, 2], 0), ([2, 0, 6], 2),
])
def test_linear_trend_matches_known_counts(counts, expected_slope):
    dates = []
    for day, count in enumerate(counts, start=1):
        dates.extend([f"2026-11-{day:02d}"] * count)
    records = prepare_records(pd.DataFrame({
        "dateadded": dates, "url_status": ["online"] * len(dates),
    }))
    result = calculate_daily_trend(records)
    assert result["slope"] == pytest.approx(expected_slope, abs=1e-10)
    assert result["daily"]["url_count"].tolist() == counts
    fitted = result["daily"]["trend_count"]
    assert fitted.iloc[1] - fitted.iloc[0] == pytest.approx(expected_slope, abs=1e-10)
    if counts == [1, 3, 5]:
        assert result["intercept"] == pytest.approx(1)
        assert fitted.tolist() == pytest.approx(counts)


@pytest.mark.parametrize("dates", [[], ["2026-11-01"], [None]])
def test_linear_trend_requires_two_reporting_days(dates):
    records = prepare_records(pd.DataFrame({
        "dateadded": dates, "url_status": ["online"] * len(dates),
    }))
    result = calculate_daily_trend(records)
    assert result["slope"] is None
    assert result["intercept"] is None
    assert result["daily"]["trend_count"].isna().all()
