# Malicious URL Explorer

## Authors

- **Author #1: Thel Nu Zaw** — [@ThelNuZaw](https://github.com/ThelNuZaw) — data collection, storage, and Fetch page.
- **Author #2: Kiana Bakrani** — [@kiana-bakrani](https://github.com/kiana-bakrani) — data analysis, visualization, and Results page.

## Project Description

Malicious URL Explorer is a Python application that uses URLhaus data to explore reported malware distribution URLs by threat category, tag, hosting country, and date.
Users will collect recent records through a Flask web interface and filter the dataset by date and threat category or tag.
The application will store defanged URL records locally as CSV files, with cached hosting-country lookups to reduce repeated requests.
It will summarize URL counts by country and category, calculate daily additions and offline percentages, and estimate observed online durations when repeated status observations are available.
A world map with page filters and a time-series chart will help users compare geographic patterns and changes over time without opening the reported URLs.

## Run on a Mac — start here

Use **Python 3.11 or newer**; the project was tested on macOS with Python 3.13.9.
The runtime package versions tested are pinned in `requirements.txt`. No hosting
or deployment is needed: Flask runs locally in your browser.

### First-time setup

Open Terminal and run these commands. If you already cloned the repository,
start from its directory and skip the first two lines.

```bash
git clone https://github.com/kiana-bakrani/CS122-Malicious_URL_Explorer.git
cd CS122-Malicious_URL_Explorer
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p data/cache
curl --fail --location https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson -o data/cache/countries.geojson
```

Internet access is needed to install packages and download the map boundaries.
If `python3 --version` is older than 3.11, install a newer Python before proceeding.

### Try the full interface with sample data — no API key needed

```bash
.venv/bin/python demo.py
URL_EXPLORER_DEMO=1 .venv/bin/python -m flask --app app run --port 5124
```

Keep Terminal running and open **http://127.0.0.1:5124/fetch**. Search the generated
records, then choose **View Results**. You can also open
**http://127.0.0.1:5124/results** directly to try filters, charts, and exports.

Both pages clearly label the records as invented sample data. Demo mode uses
`data/demo/`, never calls the live URLhaus API, and does not replace the real
`data/filtered_urls.csv`. It demonstrates the interface and analysis; it does not
represent a live-data collection run. Stop the server with **Control+C**.

### Use real URLhaus data

1. Stop a running demo server with Control+C.
2. Copy `.env.example` to `.env` and set `URLHAUS_AUTH_KEY` to your own free
   abuse.ch key. Keep this file local; do not commit credentials.
3. Follow **Hosting-country lookup** below to install the DB-IP country database.
   Without it, newly collected country values can remain `Unknown`.
4. Start Flask without the demo setting:

```bash
unset URL_EXPLORER_DEMO
.venv/bin/python -m flask --app app run --port 5124
```

Open **http://127.0.0.1:5124/fetch**, choose the search/date/threat/tag settings,
click **Search**, then **View Results**. Downloads use a five-minute cache.
If an existing `data/filtered_urls.csv` is available, you can open Results directly
without a key or a new download. Copy its matching `.metadata.json` file too if you
want the original Fetch settings to appear.

### Troubleshooting

- **Port already in use:** stop the previous server, or use `--port 5125` and open
  `http://127.0.0.1:5125/results` instead.
- **No records:** broaden the search on Fetch. Results can only narrow the saved dataset.
- **Map boundaries missing:** rerun the `mkdir` and `curl` commands above from the
  repository directory. These boundaries are separate from the DB-IP lookup database.
- **Missing URLhaus key:** use the sample-data route or configure `.env` for live Fetch.
- **No matching metadata:** imported CSVs remain usable; the original Fetch
  selections cannot be reconstructed reliably from their records.

### Optional automated checks

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

The tests use temporary files and mocked download requests; they do not require
an API key and do not visit reported malware URLs.

## Project Outline / Plan

- **Interface:** Build a Flask web interface with a Fetch page owned by Author #1 and a Results page owned by Author #2, with at least ten interactive controls across the two pages.
- **Data collection and storage (Author #1 — Thel Nu Zaw):** Retrieve URLhaus metadata, organize defanged URL records in local CSV files, and cache hosting-country lookups.
- **Data analysis (Author #2 — Kiana Bakrani):** Summarize records by country, threat category, and tag; count daily additions; calculate offline percentages; and estimate observed online durations when repeated observations are available.
- **Visualization and summary storage (Author #2 — Kiana Bakrani):** Create a world map and daily time-series chart, support filtering and plot export, and save summary CSV files locally.

### Interface Plan

We plan to build a Python Flask application with two pages, one implemented by each author.

| Page | Owner | Planned interactive controls |
| --- | --- | --- |
| Fetch | Thel Nu Zaw (Author #1) | Start-date input, end-date input, threat/tag filter, Fetch button, preview-table pagination control, Results navigation button |
| Results | Kiana Bakrani (Author #2) | Country dropdown, status dropdown, map/time-series toggle, line-grouping dropdown, Apply filters button, Save Plot button, Fetch navigation button |

This provides at least twelve interactive controls across two pages. The Fetch page will also show a progress/status label and a preview table. The Results page will show the selected visualization and summary statistics, and display a clear message when filters return no records. The shared interface outline is preliminary; each author will refine their own page during implementation.

### Data Collection and Storage Plan (written by Author #1)

**Author: Thel Nu Zaw**

I will use Python's `requests` library to retrieve publicly available malicious URL metadata from the URLhaus Community API. The application will authenticate using a free abuse.ch Auth-Key stored in a local environment variable to prevent exposing credentials in the GitHub repository. I will implement the data collection process through the Flask Fetch page, allowing users to select a start date, end date, and threat category or malware tag before retrieving and filtering records. Since the recent URLhaus export covers the past 30 days, date selections will be limited to the available data range. I will also implement error handling for network failures, unsuccessful API responses, and invalid date ranges.

After retrieving the data, I will use pandas to organize the records into a consistent tabular structure containing the URLhaus record ID, defanged URL, date added, threat category, malware tags, URL status, and available host information. I will validate required fields, normalize timestamps to UTC, and remove duplicate records using their unique URLhaus IDs where available. The application will process URL metadata only and will not visit suspicious URLs or download malicious files.

I will store the cleaned records locally as CSV files at `data/cleaned_urls.csv` and `data/filtered_urls.csv`, using consistent column names and UTF-8 encoding so they can be accessed by the data analysis component. To support geographic visualization, I will implement a hosting-country lookup process using available host or IP information and cache successful lookups locally under `data/cache/`. Missing or unresolved country information will be labeled as `Unknown`, and cached results will reduce unnecessary repeated requests to external geolocation services.

The Fetch page will display the data retrieval status, the number of records collected, and a paginated preview table. Users will be able to navigate to the Results page after data collection is complete. I will also implement a refresh mechanism that reuses locally stored records when appropriate and respects URLhaus's minimum five-minute refresh interval. Downloaded datasets, cached lookups, and authentication credentials will be excluded from Git, while the repository will include setup instructions and documentation explaining the CSV structure and data collection process.

### Data Analysis and Visualization Plan (written by Author #2)

**Author: Kiana Bakrani**

I will use pandas to clean and analyze the CSV records supplied by Author #1, parse dates in UTC, and remove duplicate URL records using the URLhaus record ID where available. I will group records by hosting country and threat category, compare malware tags where the threat field has little variation, and count newly reported URLs per day using their date-added values. Daily counts describe additions to URLhaus rather than the dates attacks first occurred. Missing hosting-country values will remain in an Unknown group and will be reported separately from countries plotted on the map.

I will calculate the percentage of records marked offline within the selected dataset and filters, showing the record counts alongside each percentage. Unknown or missing status values will be reported separately and excluded from the online/offline percentage denominator. If repeated timestamped status observations are available, I will estimate observed online durations from the first online observation to the first subsequent offline observation; URLs still online will be marked ongoing. A single snapshot will support status percentages, but will not be treated as evidence of a URL's full online lifetime.

I will create a Matplotlib world choropleth map showing URL counts by hosting country and a time-series chart showing newly reported URLs per day, split by threat category or the most frequent malware tags in the saved selection. Each plot will include a descriptive title, date range, legend or color scale, and labeled axes where applicable. Hosting country represents infrastructure location, not the location or nationality of an attacker. Since a record can have several tags, tag-group totals can overlap and will be labeled accordingly.

I will implement the Results page with country and status filters, leaving URL search, date, threat, and tag selection on Fetch, a map/time-series toggle, and a Save Plot button that exports the currently displayed visualization as a PNG image. I will also save summary CSV files by country, threat category, and date under `data/summaries/`, keeping downloaded records and generated summaries out of Git.

## Data Source and Access

The planned source is the [URLhaus Community API](https://urlhaus.abuse.ch/api/). Its recent export covers URLs added within the past 30 days, so available date filters will reflect the downloaded coverage. Access requires a free abuse.ch Auth-Key, which will be kept in local configuration and excluded from Git. Downloads will respect the documented minimum five-minute refresh interval.

URLhaus focuses on malware distribution URLs; the threat field may offer limited variety, so malware tags will provide additional comparison categories. The application will process metadata and display URLs as defanged text without fetching their contents.

## License

Project code uses the [BSD 3-Clause License](LICENSE). URLhaus data remains subject to its provider's terms and attribution requirements.

## Country lookup setup

### Map boundary setup (Author #2)

The Matplotlib country map reads Natural Earth's public-domain 1:110m country
boundaries from `data/cache/countries.geojson`. From the project directory, run:

```bash
mkdir -p data/cache
curl --fail --location https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson -o data/cache/countries.geojson
```

This boundary dataset is excluded from Git along with the other downloaded data.
It is a simplified world map; small territories may not appear, so records with
unmapped codes are reported separately. Chart counts come from the filtered
URLhaus records, not from the boundary file. The Matplotlib map is a static figure
that will be displayed on the Results page; it replaces the earlier Plotly map plan.

### Hosting-country lookup (Author #1)

Install the packages in `requirements.txt`. Download and decompress the [DB-IP IP to Country Lite MMDB](https://db-ip.com/db/download/ip-to-country-lite) into `data/cache/dbip-country-lite.mmdb`.

Each Search submission adds `country` to `data/filtered_urls.csv`. It contains a two-letter country code such as `US`, or `Unknown` when a country cannot be determined within the lookup time limit. Country estimates describe the resolved infrastructure. Successful lookups are cached for 24 hours in `data/cache/country_cache.sqlite3`. Replace the MMDB with a newer release to refresh the geolocation data.

[IP Geolocation by DB-IP](https://db-ip.com). Include this attribution on Results pages that use the country data.

## Fetch selection and Results filters

Fetch defines the dataset using URL search, dates, threat, and tag. Results narrows
that saved dataset by country and status, and controls its chart type and grouping.
To change the underlying search, return to Fetch and save a new selection.

New Fetch searches save `data/filtered_urls.metadata.json` alongside the CSV,
recording the requested filters, save time, and record count. Results displays
these settings only when the metadata matches the CSV checksum. Imported or older
CSVs still work, but their original Fetch settings are shown as unavailable.
Copy both files when sharing a dataset if you want to preserve the selection details.
The metadata and downloaded data remain excluded from Git.

Results supports PNG downloads, individual summary CSV downloads, and an explicit
**Save summaries locally** action. Local saving writes all five summaries under
`data/summaries/` on the Flask computer, replacing earlier files. Viewing Results
does not write summaries. Downloads and saves use the current country/status filters.
Online-duration estimates are unavailable in the current single-snapshot pipeline;
repeated timestamped observations would be required.

## Using Results

1. Check the saved dataset and original Fetch selections, when available.
2. Choose country/status filters, chart type, and time-series grouping, then click
   **Apply filters**. **Reset** restores the entire saved dataset.
3. Read the statistics and expand the on-page explanations if needed. Use
   **Save Plot (PNG)** or a summary CSV link to download the current analysis.
4. Expand the optional local-save section to write all five summary CSVs on the
   Flask computer. Demo mode uses `data/demo/summaries/`; live mode uses `data/summaries/`.


## Future improvements

- Retain repeated status observations to estimate observed online durations.
- Add more geographic detail for small territories absent from the simplified map.
- Offer rate-normalized comparisons when appropriate reference data is available.
- Support multiple named saved datasets instead of replacing one active selection.
