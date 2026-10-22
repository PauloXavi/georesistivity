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
