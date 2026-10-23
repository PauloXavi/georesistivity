"""Tests for non-mutating plot preparation and scale validation."""

import math

import pytest
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgb
from matplotlib.container import ErrorbarContainer

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
    SoundingErrorBar,
    SoundingFigureLabels,
    SpacingFigureLabels,
    create_sounding_figure,
    find_unplottable_sounding_points,
    sounding_axis_limits,
    sounding_decades,
    sounding_error_bar,
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


# AB/2 = 10 m, MN = 2 m: K = pi * (10^2 - 1^2) / 2 = 49.5 pi m. DeltaV = 30 and 34 mV at 50 mA
# give R = 0.60 and 0.68 ohm: mean 0.64, s = 0.08 / sqrt(2), standard error s / sqrt(2) = 0.04.
REPEATED_POSITION = (
    SheetRow(ab2="10", mn="2", delta_v="30", current="50"),
    SheetRow(ab2="10", mn="2", delta_v="34", current="50"),
)


def test_error_bar_is_one_standard_error_of_the_mean_scaled_by_k() -> None:
    (point,) = sounding(*REPEATED_POSITION)

    bar = sounding_error_bar(point)

    assert bar is not None
    assert bar.ab2_m == 10.0
    assert bar.apparent_resistivity_ohm_m == pytest.approx(31.68 * math.pi)  # 99.53 ohm.m
    assert bar.lower_ohm_m == pytest.approx(29.70 * math.pi)  # 0.60 * 49.5 pi
    assert bar.upper_ohm_m == pytest.approx(33.66 * math.pi)  # 0.68 * 49.5 pi
    assert not bar.reaches_zero


def test_single_or_excluded_readings_have_no_error_bar() -> None:
    single, excluded, negative = sounding(
        SheetRow(ab2="1", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="1,3", mn="0,5", delta_v="80", current="40"),
        SheetRow(ab2="1,3", mn="0,5", delta_v="95", current="40", excluded=True, reason="x"),
        SheetRow(ab2="1,8", mn="0,5", delta_v="-80", current="40"),
        SheetRow(ab2="1,8", mn="0,5", delta_v="-90", current="40"),
    )

    assert sounding_error_bar(single) is None
    assert sounding_error_bar(excluded) is None  # one reading left
    assert sounding_error_bar(negative) is None  # rho_a < 0 is not on the curve


def test_error_bar_reaches_zero_with_readings_of_opposite_signs() -> None:
    # R = 0.6, -0.4, and 0.1 ohm: mean 0.1, s = 0.5, standard error 0.5 / sqrt(3) > mean.
    (point,) = sounding(
        SheetRow(ab2="10", mn="2", delta_v="30", current="50"),
        SheetRow(ab2="10", mn="2", delta_v="-20", current="50"),
        SheetRow(ab2="10", mn="2", delta_v="5", current="50"),
    )

    bar = sounding_error_bar(point)

    assert bar is not None
    assert bar.lower_ohm_m == pytest.approx((0.1 - 0.5 / math.sqrt(3)) * 49.5 * math.pi)
    assert bar.reaches_zero
    assert SoundingErrorBar(1.0, 10.0, 0.0, 20.0).reaches_zero


def test_sounding_figure_draws_error_bars_in_the_segment_colour() -> None:
    points = sounding(*REPEATED_POSITION, SheetRow(ab2="13", mn="2", delta_v="20", current="50"))

    axes = create_sounding_figure(points).axes[0]

    segment = axes.get_lines()[0]
    containers = [c for c in axes.containers if isinstance(c, ErrorbarContainer)]
    drawn = [c for c in containers if c.lines[2][0].get_segments()]
    assert len(containers) == 2  # the bar of 10 m and the neutral legend entry
    assert len(drawn) == 1
    (vertical,) = drawn[0].lines[2]
    ((x_low, y_low), (x_high, y_high)) = vertical.get_segments()[0]
    assert x_low == x_high == 10.0
    assert (y_low, y_high) == pytest.approx((29.70 * math.pi, 33.66 * math.pi))
    assert tuple(vertical.get_colors()[0][:3]) == pytest.approx(
        to_rgb(segment.get_color()), abs=1e-6
    )
    assert axes.get_legend().get_texts()[-1].get_text() == (
        "\u00b11 standard error of the mean (n \u2265 2)"
    )


def test_sounding_figure_can_leave_out_error_bars() -> None:
    axes = create_sounding_figure(sounding(*REPEATED_POSITION), error_bars=False).axes[0]

    assert not [c for c in axes.containers if isinstance(c, ErrorbarContainer)]
    assert [text.get_text() for text in axes.get_legend().get_texts()] == [
        "MN = 2 m",
        "Quality warning",  # CV of 8.8% is above the 5% limit
    ]


def test_figure_without_repeated_readings_has_no_error_bar_legend() -> None:
    axes = create_sounding_figure(sounding(*OVERLAP_SOUNDING)).axes[0]

    assert not [c for c in axes.containers if isinstance(c, ErrorbarContainer)]


def test_axes_include_the_ends_of_the_error_bars() -> None:
    # AB/2 = 320 m, MN = 100 m: K = 999 pi. R = 2.6 and 3.2 ohm give rho_a = 9 104 ohm.m with a
    # standard error of 0.3 * 999 pi = 942 ohm.m, so the bar ends above 10 000 ohm.m.
    rows = (
        SheetRow(ab2="320", mn="100", delta_v="26", current="10"),
        SheetRow(ab2="320", mn="100", delta_v="32", current="10"),
    )

    with_bars = create_sounding_figure(sounding(*rows)).axes[0]
    without_bars = create_sounding_figure(sounding(*rows), error_bars=False).axes[0]

    assert with_bars.get_ylim() == (1.0, 100000.0)
    assert without_bars.get_ylim() == (1.0, 10000.0)


def test_bar_reaching_zero_is_dotted_to_the_bottom_and_circled() -> None:
    # DeltaV = 0 and 10 mV: R = 0 and 0.2 ohm, mean 0.1 = standard error, so the bar reaches
    # zero. A CV limit of 1000% leaves the point without warnings.
    points = evaluate_sheet(
        (
            SheetRow(ab2="10", mn="2", delta_v="0", current="50"),
            SheetRow(ab2="10", mn="2", delta_v="10", current="50"),
        ),
        voltage_unit="mV",
        current_unit="mA",
        cv_threshold=10.0,
    ).points
    assert points[0].warnings == ()

    axes = create_sounding_figure(points).axes[0]

    bottom = axes.get_ylim()[0]
    dotted = [
        segment
        for collection in axes.collections
        if isinstance(collection, LineCollection)
        for segment in collection.get_segments()
        if len(segment) and segment[0][1] == bottom
    ]
    assert len(dotted) == 1
    assert dotted[0][1][1] == pytest.approx(0.1 * 49.5 * math.pi)  # up to the point
    assert "Quality warning" in [text.get_text() for text in axes.get_legend().get_texts()]


def plot_area_mm(points: tuple[PointResult, ...], **options: object) -> tuple[float, float]:
    figure = create_sounding_figure(points, **options)  # type: ignore[arg-type]
    width_in, height_in = figure.get_size_inches()
    box = figure.axes[0].get_position()
    return box.width * width_in * 25.4, box.height * height_in * 25.4


def test_scaled_figure_has_the_same_decade_length_on_both_axes() -> None:
    # The field sheet minimum is 3 decades of AB/2 (1-1000 m) and 4 of rho_a (1-10 000 ohm.m).
    width_mm, height_mm = plot_area_mm(sounding(*OVERLAP_SOUNDING), decade_mm=62.5)

    assert width_mm == pytest.approx(3 * 62.5)
    assert height_mm == pytest.approx(4 * 62.5)


def test_scaled_figure_grows_with_extra_decades() -> None:
    # rho_a from 1.5e-4 to 2.8e6 ohm.m: eleven decades from 1e-4 to 1e7.
    points = sounding(
        SheetRow(ab2="320", mn="100", delta_v="9000", current="10"),
        SheetRow(ab2="1", mn="0,5", delta_v="0,01", current="400"),
    )

    assert sounding_decades(points) == (3, 11)
    assert plot_area_mm(points, decade_mm=20.0) == pytest.approx((60.0, 220.0))


def test_scaled_figure_leaves_room_for_every_title_line() -> None:
    one_line = create_sounding_figure(sounding(*OVERLAP_SOUNDING), decade_mm=50.0)
    two_lines = create_sounding_figure(
        sounding(*OVERLAP_SOUNDING),
        labels=SoundingFigureLabels(title="Sondagem\nSEV 01"),
        decade_mm=50.0,
    )

    assert one_line.get_size_inches()[1] * 25.4 == pytest.approx(15.0 + 200.0 + 4.0 + 5.5)
    assert two_lines.get_size_inches()[1] * 25.4 == pytest.approx(15.0 + 200.0 + 4.0 + 11.0)
    assert one_line.get_size_inches()[0] * 25.4 == pytest.approx(22.0 + 150.0 + 6.0)


@pytest.mark.parametrize("decade_mm", [0.0, -10.0, math.nan, math.inf])
def test_scaled_figure_needs_a_positive_modulus(decade_mm: float) -> None:
    with pytest.raises(ValueError, match="decade_mm must be a positive number"):
        create_sounding_figure(sounding(*OVERLAP_SOUNDING), decade_mm=decade_mm)


def test_axis_limits_follow_the_error_bar_option() -> None:
    rows = (
        SheetRow(ab2="320", mn="100", delta_v="26", current="10"),
        SheetRow(ab2="320", mn="100", delta_v="32", current="10"),
    )

    assert sounding_axis_limits(sounding(*rows)) == ((1.0, 1000.0), (1.0, 100000.0))
    assert sounding_axis_limits(sounding(*rows), error_bars=False)[1] == (1.0, 10000.0)
    assert sounding_decades(sounding(*rows)) == (3, 5)


def test_axis_limits_need_a_plottable_point() -> None:
    points = sounding(SheetRow(ab2="1", mn="0,5", delta_v="-80", current="40"))

    with pytest.raises(ValueError, match="positive apparent resistivity"):
        sounding_axis_limits(points)
