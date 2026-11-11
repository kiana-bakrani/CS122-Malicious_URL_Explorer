
import pandas as pd

from backend.data_storage import (
    save_cleaned_data,
    save_filtered_data,
    load_csv_data
)


def sample_dataframe():
    return pd.DataFrame({
        "id": ["101", "102"],
        "dateadded": pd.to_datetime([
            "2026-11-01",
            "2026-11-02"
        ], utc=True),
        "last_online": pd.to_datetime([
            "2026-11-03",
            None
        ], utc=True),
        "threat": [
            "malware_download",
            "malware_download"
        ],
        "tags": ["mirai", "emotet"]
    })


def test_save_cleaned_data(monkeypatch, tmp_path):
    import backend.data_storage as storage

    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)

    df = sample_dataframe()
    file_path = save_cleaned_data(df)

    assert file_path.exists()
    assert file_path.name == "cleaned_urls.csv"


def test_save_filtered_data(monkeypatch, tmp_path):
    import backend.data_storage as storage

    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)

    df = sample_dataframe().iloc[:1]
    file_path = save_filtered_data(df)

    assert file_path.exists()
    assert file_path.name == "filtered_urls.csv"


def test_load_csv_data(tmp_path):
    df = sample_dataframe()

    file_path = tmp_path / "test_urls.csv"
    df.to_csv(file_path, index=False)

    loaded_df = load_csv_data(file_path)

    assert len(loaded_df) == 2
    assert loaded_df["id"].tolist() == ["101", "102"]
    assert pd.api.types.is_datetime64_any_dtype(
        loaded_df["dateadded"]
    )
    assert pd.isna(loaded_df.loc[1, "last_online"])
