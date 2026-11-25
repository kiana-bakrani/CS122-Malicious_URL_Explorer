"""Save Author #2's analysis summaries as local CSV files."""

from pathlib import Path

import pandas as pd
from backend.data_storage import DATA_DIR

from data_visualization.analysis import (
    prepare_records,
    count_by_category,
    count_by_tag,
    count_daily_additions,
    summarize_status,
)


SUMMARY_DIR = DATA_DIR / "summaries"


def build_summaries(df):
    """Build the same summary tables for local storage and browser downloads."""
    records = prepare_records(df)
    return {
        "by_country": count_by_category(records, "country"),
        "by_threat": count_by_category(records, "threat"),
        "by_tag": count_by_tag(records),
        "daily_additions": count_daily_additions(records),
        "status_summary": pd.DataFrame([summarize_status(records)]),
    }


def save_summary_csvs(df, output_dir=SUMMARY_DIR):
    """Export five summaries, replacing previous files for the current selection.

    Returns the saved paths. Unknown offline percentages become blank cells.
    """
    summaries = build_summaries(df)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, summary in summaries.items():
        path = output_dir / f"{name}.csv"
        summary.to_csv(path, index=False, encoding="utf-8")
        paths[name] = path
    return paths
