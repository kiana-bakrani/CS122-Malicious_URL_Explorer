
from pathlib import Path
import pandas as pd

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directory for storing CSV files
DATA_DIR = PROJECT_ROOT / "data"


def save_cleaned_data(df):
    """Save all cleaned URLhaus records to CSV."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    file_path = DATA_DIR / "cleaned_urls.csv"

    df.to_csv(file_path, index=False)

    return file_path


def save_filtered_data(df):
    """Save filtered URLhaus records to CSV."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    file_path = DATA_DIR / "filtered_urls.csv"

    df.to_csv(file_path, index=False)

    return file_path


def load_csv_data(file_path):
    """Load saved URLhaus records from CSV."""

    df = pd.read_csv(
        file_path,
        dtype={"id": "string"},
        parse_dates=["dateadded", "last_online"]
    )

    return df
