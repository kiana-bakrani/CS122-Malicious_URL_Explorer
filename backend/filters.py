#threat and malware tag filtering
import pandas as pd
def filter_by_threat(df, threat=None):
    """Filter records by threat category."""

    if not threat or threat.lower() == "all":
        return df.copy()

    return df[
        df["threat"].fillna("").str.lower() == threat.lower()
    ].reset_index(drop=True)


def filter_by_tag(df, tag=None):
    """Filter records containing a specific malware tag."""

    if not tag or tag.lower() == "all":
        return df.copy()

    def has_tag(tags):
        if pd.isna(tags):
            return False

        tag_list = [
            t.strip().lower()
            for t in str(tags).split(",")
        ]

        return tag.strip().lower() in tag_list

    return df[
        df["tags"].apply(has_tag)
    ].reset_index(drop=True)
    
def filter_by_date(df, start_date=None, end_date=None):
    """Filter URLhaus records by dateadded (UTC)."""

    filtered_df = df.copy()

    if start_date:
        start = pd.to_datetime(start_date, utc=True)
        filtered_df = filtered_df[
            filtered_df["dateadded"] >= start
        ]

    if end_date:
        end = pd.to_datetime(end_date, utc=True)
        end_exclusive = end + pd.Timedelta(days=1)

        filtered_df = filtered_df[
            filtered_df["dateadded"] < end_exclusive
        ]

    return filtered_df.reset_index(drop=True)
