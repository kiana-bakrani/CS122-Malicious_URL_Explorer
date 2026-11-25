"""Generate invented records in data/demo without changing real project data."""

from datetime import datetime, timedelta, timezone
import os


def main():
    os.environ["URL_EXPLORER_DEMO"] = "1"
    import pandas as pd
    from backend.data_storage import save_cleaned_data, save_filtered_data

    first_day = datetime.now(timezone.utc).date() - timedelta(days=14)
    daily_counts = [10, 14, 7, 0, 19, 12, 16, 21, 13, 25, 18, 28, 20, 31, 24]
    countries = ["US", "DE", "CA", "BR", "JP", "Unknown"]
    tag_sets = ["zip,archive", "exe", "zip", "elf", "archive", ""]
    rows = []
    for offset, count in enumerate(daily_counts):
        date_added = datetime.combine(first_day + timedelta(days=offset), datetime.min.time(), tzinfo=timezone.utc)
        for index in range(count):
            number = len(rows) + 1
            status = ["online", "offline", "online", "unknown"][number % 4]
            rows.append({
                "id": str(number),
                "dateadded": date_added + timedelta(minutes=index),
                "url": f"https://demo.example.invalid/report/{number}",
                "url_status": status,
                "last_online": None if status == "unknown" else date_added,
                "threat": "malware_download",
                "tags": tag_sets[number % len(tag_sets)],
                "urlhaus_link": "",
                "reporter": "invented_classroom_demo",
                "hostname": "demo.example.invalid",
                "defanged_url": f"hxxps://demo[.]example[.]invalid/report/{number}",
                "country": countries[number % len(countries)],
            })
    records = pd.DataFrame(rows)
    save_cleaned_data(records)
    path = save_filtered_data(records, fetch_selection={
        "query": "", "start_date": first_day.isoformat(),
        "end_date": (first_day + timedelta(days=14)).isoformat(),
        "threat": "all", "tag": "all",
    })
    print(f"Created {len(records)} invented records at {path}.")
    print("Real data/filtered_urls.csv has not been changed.")
    print("Start the sample app with:")
    print("URL_EXPLORER_DEMO=1 .venv/bin/python -m flask --app app run --port 5124")


if __name__ == "__main__":
    main()
