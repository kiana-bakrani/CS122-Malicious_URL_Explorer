"""Exercise Matplotlib figures without a browser or a live data download."""

from io import BytesIO

import pandas as pd
import pytest

from data_visualization.analysis import prepare_records
from data_visualization.charts import create_timeseries_chart


def test_chart_displays_daily_counts_trend_and_can_save_png():
    records = prepare_records(pd.DataFrame({
        "dateadded": ["2026-11-01"] + ["2026-11-03"] * 3,
        "url_status": ["online"] * 4,
    }))
    fig = create_timeseries_chart(records)
    ax = fig.axes[0]
    assert list(ax.lines[0].get_ydata()) == [1, 0, 3]
    assert len(ax.lines) == 2
    assert "Reporting date (UTC)" == ax.get_xlabel()
    assert "+1.00" in ax.lines[1].get_label()
    image = BytesIO()
    fig.savefig(image, format="png", bbox_inches="tight")
    assert image.getvalue().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize("dates, expected_lines", [([], 0), (["2026-11-01"], 1)])
def test_chart_explains_when_trend_is_unavailable(dates, expected_lines):
    records = prepare_records(pd.DataFrame({
        "dateadded": dates, "url_status": ["online"] * len(dates),
    }))
    fig = create_timeseries_chart(records)
    assert len(fig.axes[0].lines) == expected_lines
    assert fig.axes[0].texts
