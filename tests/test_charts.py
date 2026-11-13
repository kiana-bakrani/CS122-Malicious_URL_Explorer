"""Exercise Matplotlib figures without a browser or a live data download."""

from io import BytesIO

import pandas as pd
import pytest

from data_visualization.analysis import prepare_records
from data_visualization.charts import create_timeseries_chart, create_country_map


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


def test_country_map_counts_multipolygons_once_and_reports_unmapped(tmp_path):
    import json
    ring = [[0, 0], [1, 0], [1, 1], [0, 0]]
    path = tmp_path / "countries.geojson"
    path.write_text(json.dumps({"features": [{
        "properties": {"ISO_A2_EH": "US"},
        "geometry": {"type": "MultiPolygon", "coordinates": [[ring], [ring]]},
    }]}))
    records = pd.DataFrame({"country": ["US", "US", "Unknown", "ZZ"]})
    fig = create_country_map(records, path)
    assert list(fig.axes[0].collections[0].get_array()) == [2, 2]
    assert "Mapped: 2 | Unknown/unmapped: 2" in fig.texts[0].get_text()
    fig.savefig(BytesIO(), format="png", bbox_inches="tight")


def test_country_map_explains_missing_boundaries(tmp_path):
    fig = create_country_map(pd.DataFrame({"country": []}), tmp_path / "missing")
    assert "boundaries missing" in fig.axes[0].texts[0].get_text()
