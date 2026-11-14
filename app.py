from collections import Counter
from datetime import date, datetime, timedelta, timezone

from flask import Flask, jsonify, render_template, request
from backend.country_lookup import add_countries
from backend.data_pipeline import run_pipeline, get_cleaned_data
from backend.data_storage import DATA_DIR, load_filtered_data
from backend.filters import filter_by_date, filter_by_tag, filter_by_threat
from data_visualization.analysis import prepare_records, summarize_status

app = Flask(
    __name__,
    template_folder= 'frontend/templates',
    static_folder='frontend/static'
)

MAX_DATE_DAYS = 30
PREVIEW_PAGE_SIZE = 20


def validate_date_range(start_date, end_date):
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if start.isoformat() != start_date or end.isoformat() != end_date:
            raise ValueError
    except ValueError:
        raise ValueError("Enter a valid start date and end date.") from None
    if end < start:
        raise ValueError("End date must be on or after the start date.")
    today = datetime.now(timezone.utc).date()
    if end > today:
        raise ValueError("Choose dates through today (UTC).")
    if start < today - timedelta(days=MAX_DATE_DAYS - 1):
        raise ValueError(f"Choose dates within the latest {MAX_DATE_DAYS} calendar days (UTC).")


def ranked_tags(df):
    counts = Counter()
    for value in df["tags"].dropna():
        record_tags = {tag.strip().lower() for tag in str(value).split(",")}
        counts.update(record_tags - {"", "all"})
    return sorted(counts, key=lambda tag: (-counts[tag], tag))


def snapshot_time(df):
    downloaded_at = df.attrs.get("downloaded_at")
    if downloaded_at is None:
        return None
    return datetime.fromtimestamp(downloaded_at, tz=timezone.utc)


@app.get("/fetch/tags")
def fetch_tags():
    start = request.args.get("start_date", "")
    end = request.args.get("end_date", "")
    try:
        validate_date_range(start, end)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    try:
        df = get_cleaned_data()
        downloaded_at = snapshot_time(df)
        return jsonify(
            tags=ranked_tags(filter_by_date(df, start, end)),
            downloaded_at=downloaded_at.isoformat() if downloaded_at else None,
        )
    except Exception:
        app.logger.exception("Failed to load URLhaus tags")
        return jsonify(error="Could not load URLhaus tags. Try again."), 503


@app.route('/', methods=['GET', 'POST'])
def fetch_page():
    records = []
    total_records = None
    error = None
    downloaded_at = None
    page = 1
    page_count = 1
    first_record = 0
    last_record = 0
    preview_requested = request.method == "GET" and request.args.get("saved") == "1"

    today = datetime.now(timezone.utc).date()
    earliest_date = (today - timedelta(days=MAX_DATE_DAYS - 1)).isoformat()
    start_date = earliest_date
    end_date = today.isoformat()
    filters = request.form if request.method == "POST" else request.args
    start_date = filters.get("start_date", start_date)
    end_date = filters.get("end_date", end_date)
    selected_threat = filters.get("threat", "all")
    selected_tag = filters.get("tag", "all").strip().lower() or "all"
    query = filters.get("q", "").strip()

    threats = []
    tags = []

    try:
        validate_date_range(start_date, end_date)
        end_date_min = start_date
    except ValueError as exc:
        error = str(exc)
        end_date_min = earliest_date

    try:
        filtered_df = None
        if preview_requested:
            filtered_df = load_filtered_data()
        else:
            df = get_cleaned_data()
            downloaded_at = snapshot_time(df)
            threats = sorted(df["threat"].dropna().unique().tolist())

            if error is None:
                date_records = filter_by_date(df, start_date, end_date)
                tags = ranked_tags(date_records)
                if query:
                    matches = date_records["url"].str.contains(query, case=False, regex=False, na=False)
                    matches |= date_records["defanged_url"].str.contains(query, case=False, regex=False, na=False)
                    date_records = date_records[matches]
                date_records = date_records.sort_values("dateadded", ascending=False, kind="stable")
                if request.method == "POST":
                    filtered_df = run_pipeline(
                        threat=selected_threat,
                        tag=selected_tag,
                        cleaned_data=date_records,
                    )
                else:
                    filtered_df = filter_by_tag(
                        filter_by_threat(date_records, selected_threat), selected_tag
                    )

        if filtered_df is not None:
            total_records = len(filtered_df)
            page_count = max(1, (total_records + PREVIEW_PAGE_SIZE - 1) // PREVIEW_PAGE_SIZE)
            page = min(page_count, max(1, request.args.get("page", 1, type=int)))
            offset = (page - 1) * PREVIEW_PAGE_SIZE
            last_record = min(offset + PREVIEW_PAGE_SIZE, total_records)
            first_record = offset + 1 if total_records else 0
            preview_df = filtered_df.iloc[offset:last_record].copy()
            if request.method == "GET" and not preview_requested:
                preview_df = add_countries(preview_df, DATA_DIR / "cache")
            preview_df["country"] = preview_df["country"].fillna("Unknown").replace("", "Unknown")
            preview_df["dateadded"] = preview_df["dateadded"].astype(str)
            for column in ("hostname", "tags"):
                preview_df[column] = preview_df[column].fillna("")
            records = preview_df.to_dict(orient="records")

    except FileNotFoundError:
        error = "Fetch data before opening the preview."
    except Exception as exc:
        app.logger.exception("Failed to fetch URLhaus records")
        error = error or str(exc)

    return render_template(
        "fetch.html",
        records=records,
        page=page,
        page_count=page_count,
        first_record=first_record,
        last_record=last_record,
        preview_only=preview_requested,
        saved=preview_requested or request.method == "POST",
        query=query,
        total_records=total_records,
        error=error,
        downloaded_at=downloaded_at,
        threats=threats,
        tags=tags,
        start_date=start_date,
        end_date=end_date,
        selected_threat=selected_threat,
        max_date_days=MAX_DATE_DAYS,
        today=today.isoformat(),
        earliest_date=earliest_date,
        end_date_min=end_date_min,
        selected_tag=selected_tag
    )


@app.route("/results")
def results_page():
    summary = None
    try:
        records = load_filtered_data()
        if not records.empty:
            records = prepare_records(records)
            summary = summarize_status(records)
    except FileNotFoundError:
        records = None
    return render_template("results.html", records=records, summary=summary)


if __name__ == "__main__":
    app.run(debug=True)

