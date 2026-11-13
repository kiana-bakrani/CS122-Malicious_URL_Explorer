"""Author #2: pandas analysis of the records collected by Author #1."""

import pandas as pd


def prepare_records(df):
    """Prepare a copy for analysis without changing the collected records."""
    records = df.copy()
    records["dateadded"] = pd.to_datetime(
        records["dateadded"], utc=True, errors="coerce"
    )

    # Missing IDs cannot identify duplicates; keep those rows individually.
    if "id" in records.columns:
        records["id"] = records["id"].astype("string").str.strip()
        records["id"] = records["id"].replace("", pd.NA)
        duplicate = records["id"].notna() & records["id"].duplicated()
        records = records.loc[~duplicate].copy()

    for column in ["country", "threat"]:
        if column not in records.columns:
            records[column] = "Unknown"
        records[column] = records[column].fillna("Unknown").astype(str).str.strip()
        records[column] = records[column].replace("", "Unknown")

    if "tags" not in records.columns:
        records["tags"] = ""
    records["tags"] = records["tags"].fillna("")

    records["url_status"] = (
        records["url_status"].fillna("unknown").astype(str).str.strip().str.lower()
    )
    known_status = records["url_status"].isin(["online", "offline"])
    records.loc[~known_status, "url_status"] = "unknown"
    return records.reset_index(drop=True)


def count_by_category(records, column):
    """Count URLs by country or threat, including the Unknown group."""
    return (
        records.groupby(column).size().reset_index(name="url_count")
        .sort_values(["url_count", column], ascending=[False, True])
        .reset_index(drop=True)
    )


def count_by_tag(records):
    """Count each tag once per record; different tag groups may overlap."""
    tags = records["tags"].astype(str).str.split(",").explode().str.strip().str.lower()
    tags = tags[tags.notna() & tags.ne("")]
    # explode preserves row indexes, allowing duplicate tags per URL to be removed.
    tagged = tags.rename("tag").reset_index().drop_duplicates(["index", "tag"])
    return count_by_category(tagged, "tag")


def count_daily_additions(records):
    """Count reported additions per UTC day and threat, including zero-count days.

    Invalid dates are excluded here but remain in the other summaries.
    The date represents reporting to URLhaus, not the start of an attack.
    """
    dated = records.dropna(subset=["dateadded"]).copy()
    dated["date"] = dated["dateadded"].dt.floor("D")
    if dated.empty:
        return pd.DataFrame(columns=["date", "threat", "url_count"])

    days = pd.date_range(dated["date"].min(), dated["date"].max(), freq="D")
    groups = pd.MultiIndex.from_product(
        [days, sorted(dated["threat"].unique())], names=["date", "threat"]
    )
    counts = dated.groupby(["date", "threat"]).size()
    return counts.reindex(groups, fill_value=0).reset_index(name="url_count")


def summarize_status(records):
    """Calculate offline percentage among records with a known status only."""
    online = int(records["url_status"].eq("online").sum())
    offline = int(records["url_status"].eq("offline").sum())
    known = online + offline
    return {
        "total": len(records),
        "online": online,
        "offline": offline,
        "unknown": len(records) - known,
        "offline_percentage": 100 * offline / known if known else None,
    }
