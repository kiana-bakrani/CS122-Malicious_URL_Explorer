"""Save Author #2's analysis summaries as local CSV files."""

from pathlib import Path

import pandas as pd

from data_visualization.analysis import (
    prepare_records,
    count_by_category,
    count_by_tag,
    count_daily_additions,
    summarize_status,
)


SUMMARY_DIR = Path(__file__).resolve().parent.parent / "data" / "summaries"


def save_summary_csvs(df, output_dir=SUMMARY_DIR):
    """Analyze a collected DataFrame and export five summaries.

    Calling this again replaces the previous summaries with the current selection.
    Returns the file paths so the Results page can report where they were saved.
    Unknown offline percentages are saved as blank cells, rather than zero.
    """
    records = prepare_records(df)
    summaries = {
        "by_country": count_by_category(records, "country"),
        "by_threat": count_by_category(records, "threat"),
        "by_tag": count_by_tag(records),
        "daily_additions": count_daily_additions(records),
        "status_summary": pd.DataFrame([summarize_status(records)]),
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, summary in summaries.items():
        path = output_dir / f"{name}.csv"
        summary.to_csv(path, index=False, encoding="utf-8")
        paths[name] = path
    return paths
