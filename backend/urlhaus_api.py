
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def download_recent_export():
    """Download recent URLhaus records as CSV text."""

    auth_key = os.getenv("URLHAUS_AUTH_KEY")

    if not auth_key:
        raise ValueError("Missing URLHAUS_AUTH_KEY in .env")

    url = (
        "https://urlhaus-api.abuse.ch/v2/files/exports/"
        f"{auth_key}/recent.csv"
    )

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.text

    except requests.RequestException as error:
        raise RuntimeError(
            "Failed to download URLhaus data"
        ) from error
