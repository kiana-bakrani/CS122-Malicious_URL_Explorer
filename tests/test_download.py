
from backend.urlhaus_api import download_recent_export

try:
    csv_text = download_recent_export()

    print("Download successful!")

    # Print only the CSV header and a few records
    lines = csv_text.splitlines()
    for line in lines[:15]:
        print(line[:200])

except Exception as error:
    print("Error:", error)
