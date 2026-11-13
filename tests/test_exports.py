"""Verify exported summaries with invented records and temporary files."""

import pandas as pd

from data_visualization.exports import save_summary_csvs


def test_exports_preserve_counts_and_do_not_modify_source(tmp_path):
    source = pd.DataFrame({
        "id": ["1", "2", "2"],
        "dateadded": ["2026-11-01", "2026-11-03", "2026-11-03"],
        "country": ["US", None, None],
        "threat": ["malware_download"] * 3,
        "tags": ["mirai,elf", "elf", "elf"],
        "url_status": ["online", "offline", "offline"],
    })
    original = source.copy(deep=True)
    paths = save_summary_csvs(source, tmp_path / "summaries")
    assert len(paths) == 5
    country = pd.read_csv(paths["by_country"])
    assert dict(country.values) == {"US": 1, "Unknown": 1}
    assert pd.read_csv(paths["by_threat"])["url_count"].tolist() == [2]
    assert dict(pd.read_csv(paths["by_tag"]).values) == {"elf": 2, "mirai": 1}
    daily = pd.read_csv(paths["daily_additions"])
    assert daily["url_count"].tolist() == [1, 0, 1]
    assert pd.read_csv(paths["status_summary"])["offline_percentage"].iloc[0] == 50
    assert all("Unnamed: 0" not in pd.read_csv(path) for path in paths.values())
    pd.testing.assert_frame_equal(source, original)


def test_empty_selection_replaces_old_exports_with_readable_empty_summaries(tmp_path):
    records = pd.DataFrame({
        "dateadded": ["2026-11-01"], "url_status": ["online"]
    })
    save_summary_csvs(records, tmp_path)
    paths = save_summary_csvs(records.iloc[:0], tmp_path)
    for name in ["by_country", "by_threat", "by_tag", "daily_additions"]:
        assert pd.read_csv(paths[name]).empty
    status = pd.read_csv(paths["status_summary"]).iloc[0]
    assert status["total"] == 0
    assert pd.isna(status["offline_percentage"])
