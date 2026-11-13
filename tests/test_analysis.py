"""Check analysis results using invented metadata, without network access."""

import pandas as pd
import pytest

from data_visualization.analysis import (
    prepare_records, count_by_category, count_by_tag,
    count_daily_additions, summarize_status,
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
