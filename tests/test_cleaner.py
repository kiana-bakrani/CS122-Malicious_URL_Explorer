# from backend.urlhaus_api import download_recent_export
# from backend.data_cleaner import clean_urlhaus_data

# csv_text = download_recent_export()
# df = clean_urlhaus_data(csv_text)

# print("\nTimestamp data types:")
# print(df[["dateadded", "last_online"]].dtypes)

# print("\nFirst 5 records:")
# print(df[["id", "dateadded", "last_online"]].head())

# print("\nMissing timestamps:")
# print(df[["dateadded", "last_online"]].isna().sum())

# print("\nTotal records after cleaning:", len(df))

# print("Duplicate IDs remaining:")
# print(df["id"].duplicated().sum())

# print("Missing IDs remaining:")
# print(df["id"].isna().sum())

# print("\nMissing values after cleaning")
# print(df.isna().sum())

# print("\nExtracted hostnames:")
# print(df[["id", "hostname"]].head(10).to_string(index=False))

# print("\nMissing hostnames:")
# print(df["hostname"].isna().sum())

# print("\nOriginal and Defanged URLs:")
# print(
#     df[["url", "defanged_url"]]
#     .head(5)
#     .to_string(index=False)
# )

from backend.data_cleaner import defang_url

def test_defang_url():
    assert defang_url("http://example.com/file.exe") == \
        "hxxp://example[.]com/file[.]exe"

    assert defang_url("https://example.org") == \
        "hxxps://example[.]org"

    assert defang_url(None) == ""

    print("All defanging tests passed!")