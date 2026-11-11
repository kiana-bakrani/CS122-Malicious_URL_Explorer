import pandas as pd
from backend.filters import filter_by_threat, filter_by_tag


def test_filter_by_threat():
    df = pd.DataFrame({
        "id": ["1", "2", "3"],
        "threat": [
            "malware_download",
            "phishing",
            "malware_download"
        ]
    })

    result = filter_by_threat(df, "malware_download")

    assert len(result) == 2
    assert result["id"].tolist() == ["1", "3"]


def test_filter_by_tag():
    df = pd.DataFrame({
        "id": ["1", "2", "3", "4"],
        "tags": [
            "elf, mirai",
            "emotet",
            "mirai, botnet",
            ""
        ]
    })

    result = filter_by_tag(df, "mirai")

    assert len(result) == 2
    assert result["id"].tolist() == ["1", "3"]


def test_filter_all():
    df = pd.DataFrame({
        "id": ["1", "2"],
        "threat": ["malware_download", "phishing"],
        "tags": ["mirai", "emotet"]
    })

    assert len(filter_by_threat(df, "all")) == 2
    assert len(filter_by_tag(df, "all")) == 2
