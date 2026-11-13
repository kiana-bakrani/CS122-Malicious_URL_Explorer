"""Check analysis results using invented metadata, without network access."""

import pandas as pd
import pytest

from data_visualization.analysis import (
    prepare_records, count_by_category, count_by_tag,
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



@pytest.mark.parametrize("empty", [False, True])
def test_tag_counts_handle_empty_and_untagged_records(empty):
    source = pd.DataFrame({"dateadded": [None], "url_status": [None]})
    if empty:
        source = source.iloc[:0]
    records = prepare_records(source)
    assert count_by_tag(records).empty
