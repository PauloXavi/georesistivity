"""Tests for non-mutating plot preparation and scale validation."""

import pytest

from georesistivity import (
    Measurement,
    PlotPoint,
    calculate_measurement,
    create_resistivity_figure,
    find_log_incompatible_points,
    prepare_plot_points,
)
from georesistivity.field_sheet import SheetRow, evaluate_sheet
from georesistivity.plotting import (
    SoundingFigureLabels,
    SpacingFigureLabels,
    create_sounding_figure,
    find_unplottable_sounding_points,
    sounding_segments,
)
from georesistivity.survey import PointResult


def make_result(delta_v: float, spacing: float | None):
    measurement = Measurement(
        delta_v_original=delta_v,
        voltage_unit="V",
        current_original=1.0,
        current_unit="A",
        geometric_factor_original=10.0,
        geometric_factor_unit="m",
        spacing_ab2_original=spacing,
        spacing_unit="m" if spacing is not None else None,
    )
    return calculate_measurement(measurement)


def test_plot_preparation_keeps_only_spaced_measurements_in_acquisition_order() -> None:
    results = [make_result(3.0, 30.0), make_result(2.0, None), make_result(1.0, 10.0)]

    points = prepare_plot_points(results)

    assert [point.acquisition_index for point in points] == [1, 3]
    assert [point.spacing_ab2_m for point in points] == [30.0, 10.0]


def test_optional_sort_changes_only_the_plotting_copy() -> None:
    results = [make_result(3.0, 30.0), make_result(1.0, 10.0), make_result(2.0, 20.0)]
    original_spacings = [result.spacing_ab2_m for result in results]

    points = prepare_plot_points(results, sort_by_spacing=True)

    assert [point.spacing_ab2_m for point in points] == [10.0, 20.0, 30.0]
    assert [point.acquisition_index for point in points] == [2, 3, 1]
    assert [result.spacing_ab2_m for result in results] == original_spacings


def test_log_incompatible_points_are_reported_by_acquisition_index() -> None:
    points = (
        PlotPoint(1, 1.0, 10.0),
        PlotPoint(2, 0.0, 20.0),
        PlotPoint(3, 3.0, -5.0),
    )

    assert find_log_incompatible_points(points) == (2, 3)


def test_log_figure_rejects_non_positive_points_without_excluding_them() -> None:
    points = (PlotPoint(1, 1.0, 10.0), PlotPoint(2, 2.0, -5.0))

    with pytest.raises(ValueError, match="incompatible rows: 2"):
        create_resistivity_figure(points, scale="log-log")


def test_figure_has_scientific_labels_and_requested_scale() -> None:
    points = (PlotPoint(1, 1.0, 10.0), PlotPoint(2, 2.0, 20.0))

    figure = create_resistivity_figure(points, scale="log-log")
    axes = figure.axes[0]

    assert axes.get_title() == "Apparent Resistivity vs. Electrode Spacing"
    assert axes.get_xlabel() == "AB/2 [m]"
    assert axes.get_ylabel() == "Apparent resistivity [\u03a9\u00b7m]"
    assert axes.get_xscale() == "log"
    assert axes.get_yscale() == "log"


def test_figure_requires_at_least_two_points() -> None:
    with pytest.raises(ValueError, match="at least two plot points"):
        create_resistivity_figure((PlotPoint(1, 1.0, 10.0),))


def test_figure_rejects_unknown_scale() -> None:
    points = (PlotPoint(1, 1.0, 10.0), PlotPoint(2, 2.0, 20.0))

    with pytest.raises(ValueError, match="unsupported plot scale"):
        create_resistivity_figure(points, scale="semilog")  # type: ignore[arg-type]


def sounding(*rows: SheetRow) -> tuple[PointResult, ...]:
    return evaluate_sheet(rows, voltage_unit="mV", current_unit="mA").points


OVERLAP_SOUNDING = (
    SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),
    SheetRow(ab2="5,5", mn="0,5", delta_v="9", current="50"),
    SheetRow(ab2="5,5", mn="2", delta_v="33", current="50"),
    SheetRow(ab2="10", mn="2", delta_v="12", current="50"),
)


def test_sounding_segments_group_by_mn_and_order_by_ab2() -> None:
    segments = sounding_segments(sounding(*OVERLAP_SOUNDING))

    assert list(segments) == [0.5, 2.0]
    assert [point.point.ab2_m for point in segments[0.5]] == [1.0, 5.5]
    assert [point.point.ab2_m for point in segments[2.0]] == [5.5, 10.0]


def test_non_positive_and_empty_points_are_left_out_of_the_curve() -> None:
    points = sounding(
        SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="1,3", mn="0,5", delta_v="-80", current="40"),
        SheetRow(ab2="1,8", mn="0,5", delta_v="80", current="40", excluded=True, reason="x"),
    )

    assert [p.point.ab2_m for p in sounding_segments(points)[0.5]] == [1.0]
    assert [p.point.ab2_m for p in find_unplottable_sounding_points(points)] == [1.3]


def test_sounding_figure_uses_equal_decades_like_bilog_paper() -> None:
    figure = create_sounding_figure(sounding(*OVERLAP_SOUNDING))
    axes = figure.axes[0]

    assert axes.get_xscale() == "log"
    assert axes.get_yscale() == "log"
    assert axes.get_xlim() == (1.0, 1000.0)
    assert axes.get_ylim() == (1.0, 10000.0)
    assert axes.get_aspect() == 1.0
    assert axes.get_ylabel() == "Apparent resistivity [Ω·m]"
    assert [text.get_text() for text in axes.get_legend().get_texts()] == [
        "MN = 0,5 m",
        "MN = 2 m",
    ]


def test_sounding_figure_extends_axes_to_whole_decades_beyond_the_paper() -> None:
    points = sounding(
        SheetRow(ab2="320", mn="100", delta_v="9000", current="10"),
        SheetRow(ab2="1", mn="0,5", delta_v="0,01", current="400"),
    )

    axes = create_sounding_figure(points, number_format="en").axes[0]

    assert axes.get_xlim() == (1.0, 1000.0)
    assert axes.get_ylim() == (0.0001, 10000000.0)  # rho_a from 1.5e-4 to 2.8e6


def test_sounding_figure_circles_points_with_warnings() -> None:
    points = sounding(
        SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="1,3", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="1,3", mn="0,5", delta_v="95", current="40"),
    )

    legend = create_sounding_figure(points).axes[0].get_legend()

    assert "Quality warning" in [text.get_text() for text in legend.get_texts()]


def test_sounding_figure_needs_a_plottable_point() -> None:
    points = sounding(SheetRow(ab2="1", mn="0,5", delta_v="-80", current="40"))

    with pytest.raises(ValueError, match="positive apparent resistivity"):
        create_sounding_figure(points)


def test_figures_accept_translated_labels() -> None:
    spacing = create_resistivity_figure(
        (PlotPoint(1, 1.0, 10.0), PlotPoint(2, 2.0, 20.0)),
        labels=SpacingFigureLabels(title="Título", x_axis="AB/2 [m]", y_axis="\u03c1a"),
    ).axes[0]
    sounding_axes = create_sounding_figure(
        sounding(*OVERLAP_SOUNDING),
        labels=SoundingFigureLabels(
            title="Sondagem", y_axis="Resistividade", mn_legend="MN de {mn} m"
        ),
    ).axes[0]

    assert spacing.get_title() == "Título"
    assert spacing.get_ylabel() == "\u03c1a"
    assert sounding_axes.get_title() == "Sondagem"
    assert sounding_axes.get_ylabel() == "Resistividade"
    assert [text.get_text() for text in sounding_axes.get_legend().get_texts()] == [
        "MN de 0,5 m",
        "MN de 2 m",
    ]
