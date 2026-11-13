
from pathlib import Path
from tempfile import NamedTemporaryFile
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

    with NamedTemporaryFile(dir=DATA_DIR, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        df.to_csv(temporary_path, index=False)
        temporary_path.replace(file_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return file_path


def load_filtered_data():
    """Read the dataset from the latest successful Fetch submission."""
    records = load_csv_data(DATA_DIR / "filtered_urls.csv")
    if "country" not in records:
        records["country"] = "Unknown"
    return records


def load_csv_data(file_path):
    """Load saved URLhaus records from CSV."""

    df = pd.read_csv(
        file_path,
        dtype={"id": "string"},
        parse_dates=["dateadded", "last_online"]
    )

    return df
