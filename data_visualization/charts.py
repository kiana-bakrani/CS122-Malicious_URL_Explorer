"""Author #2: Matplotlib figures for the Results page and plot downloads."""

import json
from pathlib import Path

import numpy as np
import pycountry
import matplotlib.dates as mdates
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm, LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from data_visualization.analysis import calculate_daily_trend, count_daily_groups


def country_display_names():
    """Look up ISO country names independently of map boundary coverage."""
    return {
        country.alpha_2: getattr(country, "common_name", country.name)
        for country in pycountry.countries
    }


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


def create_country_map(records, boundary_path=None, selected_country="all", reference_records=None, status_label=None):
    """Color Natural Earth country polygons using prepared hosting-country codes.

    Boundary data is downloaded separately into data/cache, not stored in Git.
    Unknown/unmapped records are reported separately, never assigned a location.
    Pass all countries for the active status selection. Country selection adds an
    outline only; reference_records fixes the color scale to the saved dataset.
    """
    if boundary_path is None:
        boundary_path = Path(__file__).resolve().parent.parent / "data/cache/countries.geojson"
    fig = Figure(figsize=(10, 5.5), layout="constrained")
    ax = fig.subplots()
    title = "Reported URLs by hosting country"
    if status_label:
        title += " — " + ("all statuses" if status_label == "all" else status_label)
    ax.set_title(title, loc="left", fontweight="bold")
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
    highlighted = []
    selected_name = selected_country
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
            if code == selected_country:
                highlighted.append(part[0])
                selected_name = properties.get("NAME_EN", code)

    reference = records if reference_records is None else reference_records
    reference_counts = reference["country"].astype(str).str.strip().str.upper().value_counts()
    mapped_counts = reference_counts[reference_counts.index.isin(mapped_codes)]
    # Logarithms need positive limits. A minimum decade also handles 0/1-only data.
    maximum = max(int(mapped_counts.max()), 10) if not mapped_counts.empty else 10
    cmap = LinearSegmentedColormap.from_list(
        "url_counts", ["#c6dbef", "#6baed6", "#2171b5", "#08306b"]
    )
    cmap.set_bad("#e2e5e9")
    collection = PolyCollection(polygons, edgecolors="gray", linewidths=0.3,
                                cmap=cmap, norm=LogNorm(vmin=1, vmax=maximum))
    collection.set_array(np.ma.masked_less_equal(np.asarray(values), 0))
    ax.add_collection(collection)
    legend_items = [Patch(facecolor="#e2e5e9", edgecolor="gray", label="0 reported URLs in this selection")]
    if highlighted:
        ax.add_collection(PolyCollection(
            highlighted, facecolors="none", edgecolors="#c35400", linewidths=1.8, zorder=3,
        ))
        label = f"Selected: {selected_name} ({int(counts.get(selected_country, 0))} URLs)"
        legend_items.append(Patch(facecolor="none", edgecolor="#c35400", label=label))
    elif selected_country != "all":
        ax.text(0.02, 0.13, f"{selected_country}: no boundary to outline",
                transform=ax.transAxes, fontsize=8,
                bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "none"})
    ax.legend(handles=legend_items, loc="lower left", fontsize=8)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 90)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ticks = [10 ** power for power in range(int(np.log10(maximum)) + 1)]
    if ticks[-1] != maximum:
        ticks.append(maximum)
    colorbar = fig.colorbar(
        collection, ax=ax, shrink=0.7, ticks=ticks,
        label="Reported URL count (logarithmic; fixed dataset scale)",
    )
    colorbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda value, position: f"{value:,.0f}"))
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
