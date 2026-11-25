
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
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


def save_filtered_data(df, fetch_selection=None):
    """Save filtered URLhaus records to CSV."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    file_path = DATA_DIR / "filtered_urls.csv"

    with NamedTemporaryFile(dir=DATA_DIR, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        df.to_csv(temporary_path, index=False)
        fingerprint = sha256(temporary_path.read_bytes()).hexdigest()
        temporary_path.replace(file_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    # Keep provenance separate from tabular records. A checksum prevents showing
    # old selections if someone copies a different CSV into the data directory.
    metadata_path = DATA_DIR / "filtered_urls.metadata.json"
    if fetch_selection is None:
        metadata_path.unlink(missing_ok=True)
    else:
        metadata = {
            "csv_sha256": fingerprint,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(df),
            "selection": fetch_selection,
        }
        with NamedTemporaryFile(dir=DATA_DIR, delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            temporary_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            temporary_path.replace(metadata_path)
        finally:
            temporary_path.unlink(missing_ok=True)
    return file_path


def load_filtered_data():
    """Read the dataset from the latest successful Fetch submission."""
    csv_bytes = (DATA_DIR / "filtered_urls.csv").read_bytes()
    records = load_csv_data(BytesIO(csv_bytes))
    records.attrs["snapshot_id"] = sha256(csv_bytes).hexdigest()
    if "country" not in records:
        records["country"] = "Unknown"
    try:
        metadata = json.loads((DATA_DIR / "filtered_urls.metadata.json").read_text(encoding="utf-8"))
        if (isinstance(metadata, dict)
                and metadata.get("csv_sha256") == records.attrs["snapshot_id"]
                and isinstance(metadata.get("selection"), dict)):
            records.attrs["fetch_metadata"] = metadata
    except (OSError, ValueError):
        # Imported CSVs and older datasets may not have selection metadata.
        pass
    return records


def load_csv_data(file_path):
    """Load saved URLhaus records from CSV."""

    df = pd.read_csv(
        file_path,
        dtype={"id": "string"},
        parse_dates=["dateadded", "last_online"]
    )

    return df
