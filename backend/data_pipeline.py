from backend.urlhaus_api import download_recent_export
from backend.data_cleaner import clean_urlhaus_data
from backend.data_storage import save_cleaned_data, save_filtered_data
from backend.filters import (
    filter_by_date,
    filter_by_threat,
    filter_by_tag
)

import time

from backend.data_storage import (
    DATA_DIR,
    save_cleaned_data,
    load_csv_data
)
from backend.urlhaus_api import download_recent_export
from backend.data_cleaner import clean_urlhaus_data

CACHE_SECONDS = 300 # might change it later
def get_cleaned_data():
    """Return cached URLhaus data or download fresh data."""

    cache_path = DATA_DIR / "cleaned_urls.csv"

    # Check whether the cache exists
    if cache_path.exists():
        cache_age = time.time() - cache_path.stat().st_mtime

        # Use cached data if less than 5 minutes old
        if cache_age < CACHE_SECONDS:
            print("Using cached URLhaus data.")
            return load_csv_data(cache_path)

    # Download new data if cache is missing or expired
    print("Downloading fresh URLhaus data...")

    csv_text = download_recent_export()
    df = clean_urlhaus_data(csv_text)

    if df.empty:
        raise ValueError("No URLhaus records were downloaded.")

    save_cleaned_data(df)

    return df

def run_pipeline(start_date=None, end_date=None, threat=None, tag=None):
    """Download, clean, filter, and save URLhaus records."""

    # Step 1: Download URLhaus CSV data
    csv_text = download_recent_export()

    # Step 2: Clean and standardize records
    df = clean_urlhaus_data(csv_text)

    if df.empty:
        raise ValueError("No URLhaus records were downloaded.")

    # Step 3: Save all cleaned records
    cleaned_path = save_cleaned_data(df)

    # Step 4: Apply user-selected filters
    filtered_df = filter_by_date(df, start_date, end_date)
    filtered_df = filter_by_threat(filtered_df, threat)
    filtered_df = filter_by_tag(filtered_df, tag)

    # Step 5: Save filtered records
    filtered_path = save_filtered_data(filtered_df)

    print(f"Cleaned records: {len(df)}")
    print(f"Filtered records: {len(filtered_df)}")
    print(f"Cleaned CSV saved to: {cleaned_path}")
    print(f"Filtered CSV saved to: {filtered_path}")

    return filtered_df