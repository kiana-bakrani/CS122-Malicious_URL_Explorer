"""Author #2: Matplotlib figures for the Results page and plot downloads."""

import matplotlib.dates as mdates
from matplotlib.figure import Figure

from data_visualization.analysis import calculate_daily_trend


def create_timeseries_chart(records):
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

    ax.plot(
        daily["date"], daily["url_count"],
        color="steelblue", marker="o", markersize=4, label="Daily additions",
    )
    if result["slope"] is not None:
        ax.plot(
            daily["date"], daily["trend_count"], color="darkorange",
            linestyle="--",
            label=f"Linear trend (daily count change: {result['slope']:+.2f} per day)",
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
        f"{start} to {end} UTC | Source: URLhaus | Reporting dates, not attack start dates; trend is not a forecast.",
        fontsize=8,
    )
    return fig
