"""Author #2: Matplotlib figures for the Results page and plot downloads."""

import json
from pathlib import Path

import numpy as np
import matplotlib.dates as mdates
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from data_visualization.analysis import calculate_daily_trend, count_daily_groups


def country_display_names():
    """Use names from the local boundary file; codes still work if it is absent."""
    path = Path(__file__).resolve().parent.parent / "data/cache/countries.geojson"
    try:
        with path.open(encoding="utf-8") as source:
            features = json.load(source)["features"]
        return {
            feature["properties"]["ISO_A2_EH"]: feature["properties"]["NAME_EN"]
            for feature in features
            if len(feature["properties"].get("ISO_A2_EH", "")) == 2
        }
    except (OSError, ValueError, KeyError):
        return {}


def create_timeseries_chart(records, group_by="total", selected_tags=None):
    """Plot prepared records as daily totals with a NumPy linear trend.

    Pass an already filtered selection to chart a country, threat, or tag.
    Returns a Figure so Flask can save it without opening a desktop window.
    """
    result = calculate_daily_trend(records)
    daily = result["daily"]
    fig = Figure(figsize=(10, 4.8), layout="constrained")
    ax = fig.subplots()
    ax.set_title("Daily URLhaus additions", loc="left", fontweight="bold")
    ax.set_xlabel("Reporting date (UTC)")
    ax.set_ylabel("Newly reported URLs per day")

    if daily.empty:
        ax.text(
            0.5, 0.5, "No valid reporting dates in this selection.",
            transform=ax.transAxes, ha="center", va="center",
        )
        return fig

    group_note = ""
    if group_by == "total":
        ax.plot(daily["date"], daily["url_count"], color="steelblue",
                marker="o", markersize=4, label="Daily additions")
    else:
        grouped = count_daily_groups(records, group_by, selected_tags)
        if group_by == "tag":
            group_note = "Tag groups overlap; untagged records are excluded from tag lines."
            if not selected_tags:
                top_tags = grouped.groupby("group")["url_count"].sum().nlargest(10).index
                grouped = grouped[grouped["group"].isin(top_tags)]
                group_note += " Showing up to 10 most frequent tags."
        for label, values in grouped.groupby("group"):
            ax.plot(values["date"], values["url_count"], marker="o", markersize=3, label=label)
        if grouped.empty:
            ax.text(0.02, 0.95, "No matching tags have valid reporting dates.",
                    transform=ax.transAxes, va="top")
    if result["slope"] is not None:
        ax.plot(
            daily["date"], daily["trend_count"], color="darkorange",
            linestyle="--",
            label=f"Overall linear trend (daily count change: {result['slope']:+.2f} per day)",
        )
    else:
        ax.text(
            0.02, 0.95, "Trend requires at least two reporting days.",
            transform=ax.transAxes, va="top",
        )

    locator = mdates.AutoDateLocator(tz="UTC", minticks=3, maxticks=7)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator, tz="UTC"))
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5)
    # Keep negative fitted values visible: a fitted line is not a count forecast.
    if result["slope"] is None or daily["trend_count"].min() >= 0:
        ax.set_ylim(bottom=0)
    ax.legend(loc="best", fontsize=8)
    start = daily["date"].iloc[0].strftime("%Y-%m-%d")
    end = daily["date"].iloc[-1].strftime("%Y-%m-%d")
    fig.text(
        0.01, -0.04,
        f"{start} to {end} UTC | Source: URLhaus | Reporting dates, not attack start dates; trend is not a forecast."
        + (f"\n{group_note}" if group_note else ""),
        fontsize=8,
    )
    return fig


def create_country_map(records, boundary_path=None):
    """Color Natural Earth country polygons using prepared hosting-country codes.

    Boundary data is downloaded separately into data/cache, not stored in Git.
    Unknown/unmapped records are reported separately, never assigned a location.
    """
    if boundary_path is None:
        boundary_path = Path(__file__).resolve().parent.parent / "data/cache/countries.geojson"
    fig = Figure(figsize=(10, 5.5), layout="constrained")
    ax = fig.subplots()
    ax.set_title("Reported URLs by hosting country", loc="left", fontweight="bold")
    if not Path(boundary_path).is_file():
        ax.text(0.5, 0.5, "Map boundaries missing. Follow the README map setup.",
                transform=ax.transAxes, ha="center", va="center")
        ax.set_axis_off()
        return fig

    with Path(boundary_path).open(encoding="utf-8") as source:
        features = json.load(source)["features"]
    counts = records["country"].astype(str).str.strip().str.upper().value_counts()
    polygons = []
    values = []
    mapped_codes = set()
    for feature in features:
        properties = feature["properties"]
        code = properties.get("ISO_A2_EH", properties.get("ISO_A2", ""))
        if len(code) != 2:
            code = ""
        if code:
            mapped_codes.add(code)
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            parts = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            parts = geometry["coordinates"]
        else:
            continue
        for part in parts:
            polygons.append(part[0])
            values.append(int(counts.get(code, 0)))

    collection = PolyCollection(polygons, edgecolors="gray", linewidths=0.3,
                                cmap="Blues", norm=Normalize(0, max(values + [1])))
    collection.set_array(np.asarray(values))
    ax.add_collection(collection)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 90)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    fig.colorbar(collection, ax=ax, shrink=0.7, label="Reported URL count")
    mapped = int(counts[counts.index.isin(mapped_codes)].sum())
    date_note = ""
    if "dateadded" in records:
        dates = records["dateadded"].dropna()
        if not dates.empty:
            date_note = f"Reporting dates: {dates.min():%Y-%m-%d} to {dates.max():%Y-%m-%d} UTC | "
    fig.text(0.01, -0.03,
             date_note + f"Mapped: {mapped} | Unknown/unmapped: {len(records) - mapped}\n"
             "Hosting location, not attacker origin.\n"
             "Sources: URLhaus; Natural Earth (public domain); IP Geolocation by DB-IP (db-ip.com).",
             fontsize=8)
    return fig
