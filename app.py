from flask import Flask, render_template, request
from backend.data_pipeline import run_pipeline, get_cleaned_data

app = Flask(
    __name__,
    template_folder= 'frontend/templates',
    static_folder='frontend/static'
)

@app.route('/', methods=['GET', 'POST'])
def fetch_page():
    records = []
    total_records = None
    error = None

    start_date = ""
    end_date = ""
    selected_threat = "all"
    selected_tag = "all"

    threats = []
    tags = []

    try:
        # Load available records to populate dropdowns
        df = get_cleaned_data()

        threats = sorted(
            df["threat"].dropna().unique().tolist()
        )

        # A record may contain multiple comma-separated tags
        tags = sorted({
            tag.strip()
            for value in df["tags"].dropna()
            for tag in str(value).split(",")
            if tag.strip()
        })

        if request.method == "POST":
            start_date = request.form.get("start_date", "")
            end_date = request.form.get("end_date", "")
            selected_threat = request.form.get("threat", "all")
            selected_tag = request.form.get("tag", "all")

            filtered_df = run_pipeline(
                start_date=start_date,
                end_date=end_date,
                threat=selected_threat,
                tag=selected_tag
            )

            total_records = len(filtered_df)

            # Preview only the first 20 records
            preview_df = filtered_df.head(20).copy()

            # Convert timestamps to strings for display
            for column in ["dateadded", "last_online"]:
                preview_df[column] = preview_df[column].astype(str)

            records = preview_df.to_dict(orient="records")

    except Exception as exc:
        app.logger.exception("Failed to fetch URLhaus records")
        error = str(exc)

    return render_template(
        "fetch.html",
        records=records,
        total_records=total_records,
        error=error,
        threats=threats,
        tags=tags,
        start_date=start_date,
        end_date=end_date,
        selected_threat=selected_threat,
        selected_tag=selected_tag
    )


@app.route("/results")
def results_page():
    return render_template("results.html")


if __name__ == "__main__":
    app.run(debug=True)

