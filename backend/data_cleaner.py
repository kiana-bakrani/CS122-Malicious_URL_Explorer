import pandas as pd
from io import StringIO
from urllib.parse import urlsplit


def clean_urlhaus_data(csv_text):
    """Convert URLhaus CSV text into a pandas DataFrame."""

    df = pd.read_csv(
        StringIO(csv_text),
        comment="#",
        header=None,
        names=[
            "id",
            "dateadded",
            "url",
            "url_status",
            "last_online",
            "threat",
            "tags",
            "urlhaus_link",
            "reporter"
        ],
        dtype={"id": "string"},
        on_bad_lines="skip"
    )
    
    # Normalize timestamps to UTC
    df["dateadded"] = pd.to_datetime(
        df["dateadded"],
        utc=True,
        errors="coerce"
    )

    df["last_online"] = pd.to_datetime(
        df["last_online"],
        utc=True,
        errors="coerce"
    )
    # Count duplicate IDs before cleaning
    duplicate_count = df["id"].duplicated().sum()

    # Remove records with missing IDs
    df = df.dropna(subset=["id"])

    # Remove duplicate IDs, keeping the first occurrence
    df = df.drop_duplicates(subset=["id"], keep="first")

    # Reset row indexes
    df = df.reset_index(drop=True)
    
    # Handle missing values
    df["tags"] = df["tags"].fillna("")

    df["url_status"] = df["url_status"].fillna("unknown")
    df["threat"] = df["threat"].fillna("unknown")
    df["reporter"] = df["reporter"].fillna("unknown")
    
    # Extract hostnames for future country lookups
    df["hostname"] = df["url"].apply(extract_hostname)
    # Create a defanged URL for safe display
    df["defanged_url"] = df["url"].apply(defang_url)
    
    return df

def extract_hostname(url):
    """Extract the hostname from a URL safely."""
    if not isinstance(url, str) or not url.strip():
        return None

    try:
        return urlsplit(url).hostname
    except ValueError:
        return None
    
def defang_url(url):
    """Convert a URL into a safer, non-clickable representation."""

    if not isinstance(url, str) or not url.strip():
        return ""

    url = url.replace("http://", "hxxp://", 1)
    url = url.replace("https://", "hxxps://", 1)

    url = url.replace(".", "[.]")

    return url