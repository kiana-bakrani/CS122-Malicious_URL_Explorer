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


@pytest.mark.parametrize("group_by, expected", [
    ("threat", {"a": [2, 0, 0], "b": [0, 0, 1]}),
    ("tag", {"elf": [1, 0, 1], "mirai": [1, 0, 0]}),
])
def test_grouped_lines_share_dates_and_do_not_duplicate_tags(group_by, expected):
    records = prepare_records(pd.DataFrame({
        "dateadded": ["2026-11-01", "2026-11-01", "2026-11-03"],
        "threat": ["a", "a", "b"], "tags": ["mirai, mirai,elf", "", "elf"],
        "url_status": ["online"] * 3,
    }))
    fig = create_timeseries_chart(records, group_by)
    lines = {line.get_label(): list(line.get_ydata()) for line in fig.axes[0].lines}
    for label, counts in expected.items():
        assert lines[label] == counts
    assert any(label.startswith("Overall linear trend") for label in lines)
    if group_by == "tag":
        assert "Tag groups overlap" in fig.texts[0].get_text()
    fig.savefig(BytesIO(), format="png", bbox_inches="tight")


def test_tag_chart_only_shows_selected_tag_lines():
    records = prepare_records(pd.DataFrame({
        "dateadded": ["2026-11-01", "2026-11-03"],
        "tags": ["mirai,elf", "elf"], "url_status": ["online"] * 2,
    }))
    fig = create_timeseries_chart(records, "tag", ["mirai"])
    labels = [line.get_label() for line in fig.axes[0].lines]
    assert "mirai" in labels
    assert "elf" not in labels


def test_country_selection_preserves_comparison_and_reference_scale(tmp_path):
    import json
    features = []
    for code, longitude in [("US", 0), ("CA", 5)]:
        ring = [[longitude, 0], [longitude + 1, 0], [longitude + 1, 1], [longitude, 0]]
        features.append({"properties": {"ISO_A2_EH": code},
                         "geometry": {"type": "Polygon", "coordinates": [ring]}})
    path = tmp_path / "boundaries.json"
    path.write_text(json.dumps({"features": features}))
    reference = pd.DataFrame({"country": ["US"] * 3 + ["CA"] + ["Unknown"] * 8})
    status_selection = pd.DataFrame({"country": ["US", "CA", "Unknown"]})
    for country, longitude in [("US", 0), ("CA", 5)]:
        fig = create_country_map(status_selection, path, selected_country=country, reference_records=reference)
        colors, outline = fig.axes[0].collections
        assert list(colors.get_array()) == [1, 1]  # Other country remains visible.
        assert colors.norm.vmax == 10  # Fixed minimum decade, not selected country/status.
        assert outline.get_paths()[0].vertices[0][0] == longitude
        assert any(country in text.get_text() for text in fig.axes[0].get_legend().get_texts())
    unknown = create_country_map(status_selection, path, selected_country="Unknown", reference_records=reference)
    assert len(unknown.axes[0].collections) == 1
    assert "no boundary" in unknown.axes[0].texts[0].get_text()


@pytest.mark.parametrize("countries", [[], ["US"], ["US"] * 1000 + ["CA"] * 10])
def test_log_map_handles_zero_one_and_skewed_counts(tmp_path, countries):
    import json
    import numpy as np
    from matplotlib.colors import LogNorm
    path = tmp_path / "boundaries.json"
    path.write_text(json.dumps({"features": [
        {"properties": {"ISO_A2_EH": code},
         "geometry": {"type": "Polygon", "coordinates": [[[x, 0], [x+1, 0], [x+1, 1], [x, 0]]]}}
        for code, x in [("US", 0), ("CA", 5)]
    ]}))
    fig = create_country_map(pd.DataFrame({"country": countries}), path)
    colors = fig.axes[0].collections[0]
    assert isinstance(colors.norm, LogNorm)
    assert colors.norm.vmin == 1
    assert np.ma.getmaskarray(colors.get_array()).tolist() == ["US" not in countries, "CA" not in countries]
    if len(countries) > 1:
        assert colors.norm.vmax == 1000
        assert colors.norm(10) == pytest.approx(1/3)
        assert colors.get_array().tolist() == [1000, 10]
    fig.savefig(BytesIO(), format="png", bbox_inches="tight")
    assert "logarithmic" in fig.axes[1].get_ylabel()
