
import pandas as pd
import json

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


def test_fetch_metadata_roundtrip_and_mismatched_csv(monkeypatch, tmp_path):
    import backend.data_storage as storage
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    selection = {"query": "example", "start_date": "2026-11-01",
                 "end_date": "2026-11-02", "threat": "all", "tag": "mirai"}
    storage.save_filtered_data(sample_dataframe(), fetch_selection=selection)
    loaded = storage.load_filtered_data()
    metadata = loaded.attrs["fetch_metadata"]
    assert metadata["selection"] == selection
    assert metadata["record_count"] == 2
    assert metadata["saved_at"]
    # Simulate a copied CSV without its matching metadata.
    sample_dataframe().iloc[:1].to_csv(tmp_path / "filtered_urls.csv", index=False)
    assert "fetch_metadata" not in storage.load_filtered_data().attrs


def test_old_or_invalid_metadata_never_prevents_loading(monkeypatch, tmp_path):
    import backend.data_storage as storage
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    storage.save_filtered_data(sample_dataframe())
    assert "fetch_metadata" not in storage.load_filtered_data().attrs
    path = tmp_path / "filtered_urls.metadata.json"
    for text in ["not JSON", "[]", json.dumps({"selection": None})]:
        path.write_text(text)
        assert "fetch_metadata" not in storage.load_filtered_data().attrs


def test_save_without_selection_removes_previous_metadata(monkeypatch, tmp_path):
    import backend.data_storage as storage
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    storage.save_filtered_data(sample_dataframe(), fetch_selection={"tag": "mirai"})
    storage.save_filtered_data(sample_dataframe().iloc[:1])
    assert not (tmp_path / "filtered_urls.metadata.json").exists()
