from backend.urlhaus_api import download_recent_export
from backend.data_cleaner import clean_urlhaus_data
from backend.country_lookup import add_countries
from backend.filters import (
    filter_by_date,
    filter_by_threat,
    filter_by_tag
)

import time

from backend.data_storage import (
    DATA_DIR,
    save_cleaned_data,
    save_filtered_data,
    load_csv_data
)

# URLhaus asks clients to wait at least five minutes between export requests.
CACHE_SECONDS = 300
def get_cleaned_data():
    """Return cached URLhaus data or download fresh data."""

    cache_path = DATA_DIR / "cleaned_urls.csv"

    # Check whether the cache exists
    if cache_path.exists():
        cache_age = time.time() - cache_path.stat().st_mtime

        # Use cached data if less than 5 minutes old
        if cache_age < CACHE_SECONDS:
            print("Using cached URLhaus data.")
            df = load_csv_data(cache_path)
            df.attrs["downloaded_at"] = cache_path.stat().st_mtime
            return df

    # Download new data if cache is missing or expired
    print("Downloading fresh URLhaus data...")

    csv_text = download_recent_export()
    df = clean_urlhaus_data(csv_text)

    if df.empty:
        raise ValueError("No URLhaus records were downloaded.")

    saved_path = save_cleaned_data(df)
    df.attrs["downloaded_at"] = saved_path.stat().st_mtime

    return df

def run_pipeline(start_date=None, end_date=None, threat=None, tag=None, *, cleaned_data=None):
    """Filter and save URLhaus records from the supplied snapshot or cache."""
    df = get_cleaned_data() if cleaned_data is None else cleaned_data

    filtered_df = filter_by_date(df, start_date, end_date)
    filtered_df = filter_by_threat(filtered_df, threat)
    filtered_df = filter_by_tag(filtered_df, tag)
    filtered_df = add_countries(filtered_df, DATA_DIR / "cache")

    filtered_path = save_filtered_data(filtered_df)

    print(f"Cleaned records: {len(df)}")
    print(f"Filtered records: {len(filtered_df)}")
    print(f"Filtered CSV saved to: {filtered_path}")

    return filtered_df
