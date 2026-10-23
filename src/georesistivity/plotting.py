"""Preparation and Matplotlib rendering for spacing-based plots."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.typing import ColorType

from georesistivity.formatting import NumberFormat, format_full_precision
from georesistivity.models import MeasurementResult
from georesistivity.survey import PointResult

PlotScale = Literal["linear", "log-log"]


@dataclass(frozen=True, slots=True)
class SpacingFigureLabels:
    """Texts of the spacing figure, so interfaces can translate them."""

    title: str = "Apparent Resistivity vs. Electrode Spacing"
    x_axis: str = "AB/2 [m]"
    y_axis: str = "Apparent resistivity [\u03a9\u00b7m]"


@dataclass(frozen=True, slots=True)
class SoundingFigureLabels:
    """Texts of the sounding figure; ``mn_legend`` takes an ``{mn}`` placeholder."""

    title: str = "Vertical Electrical Sounding (Schlumberger)"
    x_axis: str = "AB/2 [m]"
    y_axis: str = "Apparent resistivity [\u03a9\u00b7m]"
    mn_legend: str = "MN = {mn} m"
    quality_warning: str = "Quality warning"
    error_bars: str = "\u00b11 standard error of the mean (n \u2265 2)"


@dataclass(frozen=True, slots=True)
class PlotPoint:
    """One plottable measurement with its original acquisition index."""

    acquisition_index: int
    spacing_ab2_m: float
    apparent_resistivity_ohm_m: float


def prepare_plot_points(
    results: Sequence[MeasurementResult],
    *,
    sort_by_spacing: bool = False,
) -> tuple[PlotPoint, ...]:
    """Select measurements with spacing and optionally sort a plotting copy."""
    points = [
        PlotPoint(
            acquisition_index=index,
            spacing_ab2_m=result.spacing_ab2_m,
            apparent_resistivity_ohm_m=result.apparent_resistivity_ohm_m,
        )
        for index, result in enumerate(results, start=1)
        if result.spacing_ab2_m is not None
    ]
    if sort_by_spacing:
        points.sort(key=lambda point: (point.spacing_ab2_m, point.acquisition_index))
    return tuple(points)


def find_log_incompatible_points(points: Sequence[PlotPoint]) -> tuple[int, ...]:
    """Return acquisition indices that cannot appear on a log-log plot."""
    return tuple(
        point.acquisition_index
        for point in points
        if point.spacing_ab2_m <= 0.0 or point.apparent_resistivity_ohm_m <= 0.0
    )


def create_resistivity_figure(
    points: Sequence[PlotPoint],
    *,
    scale: PlotScale = "linear",
    labels: SpacingFigureLabels | None = None,
) -> Figure:
    """Create a readable spacing-versus-apparent-resistivity figure."""
    if len(points) < 2:
        raise ValueError("at least two plot points are required")
    if scale not in ("linear", "log-log"):
        raise ValueError(f"unsupported plot scale: {scale!r}")

    incompatible = find_log_incompatible_points(points)
    if scale == "log-log" and incompatible:
        indices = ", ".join(str(index) for index in incompatible)
        raise ValueError(f"log-log scale requires positive values; incompatible rows: {indices}")

    figure = Figure(figsize=(8.0, 4.8), layout="constrained")
    axes = figure.subplots()
    axes.plot(
        [point.spacing_ab2_m for point in points],
        [point.apparent_resistivity_ohm_m for point in points],
        marker="o",
        linewidth=1.5,
    )
    texts = labels or SpacingFigureLabels()
    axes.set_title(texts.title)
    axes.set_xlabel(texts.x_axis)
    axes.set_ylabel(texts.y_axis)
    if scale == "log-log":
        axes.set_xscale("log")
        axes.set_yscale("log")
    axes.grid(visible=True, which="both", alpha=0.25, linewidth=0.7)
    return figure


SOUNDING_MIN_AB2_DECADES = (1.0, 1000.0)
"""Smallest AB/2 axis [m], as on the bilog field paper (1 to 1000 m)."""

SOUNDING_MIN_RHO_DECADES = (1.0, 10000.0)
"""Smallest apparent-resistivity axis [ohm.m], as on the bilog field paper (1 to 10 000)."""


def _decade_limits(values: Sequence[float], minimum: tuple[float, float]) -> tuple[float, float]:
    low = 10.0 ** math.floor(math.log10(min(values)))
    high = 10.0 ** math.ceil(math.log10(max(values)))
    return min(low, minimum[0]), max(high, minimum[1])


def sounding_segments(points: Sequence[PointResult]) -> dict[float, list[PointResult]]:
    """Group plottable points (positive rho_a) by MN [m], each segment ordered by AB/2."""
    segments: dict[float, list[PointResult]] = {}
    for point in sorted(points, key=lambda result: (result.point.mn_m, result.point.ab2_m)):
        rho_a = point.apparent_resistivity_ohm_m
        if rho_a is not None and rho_a > 0.0:
            segments.setdefault(point.point.mn_m, []).append(point)
    return segments


@dataclass(frozen=True, slots=True)
class SoundingErrorBar:
    """Error bar of one sounding point: ``rho_a +/- K * s / sqrt(n)`` [ohm.m] (decision D-10).

    The half-length is the standard error of the mean of the transfer resistances scaled by
    K (``PointResult.standard_error_ohm_m``); see Taylor, J. R., *An Introduction to Error
    Analysis*, 2nd ed., University Science Books, 1997, ch. 4.
    """

    ab2_m: float
    apparent_resistivity_ohm_m: float
    lower_ohm_m: float
    """``rho_a - standard error``; zero or negative when the bar reaches below zero."""
    upper_ohm_m: float

    @property
    def reaches_zero(self) -> bool:
        """Whether the lower end cannot be drawn on a log axis."""
        return self.lower_ohm_m <= 0.0


def sounding_error_bar(point: PointResult) -> SoundingErrorBar | None:
    """The error bar of ``point``, or ``None`` without positive rho_a or two included readings."""
    rho_a = point.apparent_resistivity_ohm_m
    error = point.standard_error_ohm_m
    if rho_a is None or rho_a <= 0.0 or error is None:
        return None
    return SoundingErrorBar(point.point.ab2_m, rho_a, rho_a - error, rho_a + error)


def _draw_error_bars(
    axes: Axes, bars: Sequence[SoundingErrorBar], color: ColorType, bottom_ohm_m: float
) -> None:
    if not bars:
        return
    # A bar that reaches zero has no lower end on a log axis: its lower half is drawn dotted
    # down to the bottom of the plot instead of ending in a cap.
    lower_errors = [
        0.0 if bar.reaches_zero else bar.apparent_resistivity_ohm_m - bar.lower_ohm_m
        for bar in bars
    ]
    upper_errors = [bar.upper_ohm_m - bar.apparent_resistivity_ohm_m for bar in bars]
    axes.errorbar(
        [bar.ab2_m for bar in bars],
        [bar.apparent_resistivity_ohm_m for bar in bars],
        yerr=[lower_errors, upper_errors],
        fmt="none",
        ecolor=color,
        elinewidth=1.0,
        capsize=3.0,
        zorder=1.9,  # under the markers, which hide the cap of a zero lower error
        clip_on=False,
    )
    below = [bar for bar in bars if bar.reaches_zero]
    if below:
        axes.vlines(
            [bar.ab2_m for bar in below],
            bottom_ohm_m,
            [bar.apparent_resistivity_ohm_m for bar in below],
            colors=color,
            linewidth=1.0,
            linestyles="dotted",
            zorder=1.9,
        )


def find_unplottable_sounding_points(points: Sequence[PointResult]) -> tuple[PointResult, ...]:
    """Return points whose apparent resistivity cannot appear on a log-log curve."""
    return tuple(
        point
        for point in points
        if point.apparent_resistivity_ohm_m is not None and point.apparent_resistivity_ohm_m <= 0
    )


def create_sounding_figure(
    points: Sequence[PointResult],
    *,
    number_format: NumberFormat = "pt-BR",
    labels: SoundingFigureLabels | None = None,
    error_bars: bool = True,
) -> Figure:
    """Draw the VES curve on log-log axes with one segment per MN.

    As on bilog field paper, the axes cover whole decades (at least 1-1000 m for AB/2 and
    1-10 000 ohm.m for rho_a) and a decade has the same length on both axes, so the curve
    keeps its shape for comparison with master curves. Points with quality warnings are
    circled in red.

    With ``error_bars``, points with two or more included readings get a bar of one standard
    error of the mean (:class:`SoundingErrorBar`). A bar that reaches zero continues dotted to
    the bottom of the plot, and its point is circled even without a warning.
    """
    segments = sounding_segments(points)
    if not segments:
        raise ValueError("at least one point with positive apparent resistivity is required")

    bars: dict[float, list[SoundingErrorBar]] = {}
    if error_bars:
        for mn_m, segment in segments.items():
            found = [sounding_error_bar(point) for point in segment]
            bars[mn_m] = [bar for bar in found if bar is not None]
    all_bars = [bar for segment_bars in bars.values() for bar in segment_bars]

    all_ab2 = [point.point.ab2_m for segment in segments.values() for point in segment]
    all_rho = [
        point.apparent_resistivity_ohm_m or 0.0
        for segment in segments.values()
        for point in segment
    ]
    all_rho += [bar.upper_ohm_m for bar in all_bars]
    all_rho += [bar.lower_ohm_m for bar in all_bars if not bar.reaches_zero]
    x_limits = _decade_limits(all_ab2, SOUNDING_MIN_AB2_DECADES)
    y_limits = _decade_limits(all_rho, SOUNDING_MIN_RHO_DECADES)

    texts = labels or SoundingFigureLabels()
    figure = Figure(figsize=(7.0, 7.0), layout="constrained")
    axes = figure.subplots()
    flagged_ab2: list[float] = []
    flagged_rho: list[float] = []
    for mn_m, segment in segments.items():
        ab2_values = [point.point.ab2_m for point in segment]
        rho_values = [point.apparent_resistivity_ohm_m or 0.0 for point in segment]
        label = format_full_precision(mn_m, number_format=number_format)
        (line,) = axes.plot(
            ab2_values,
            rho_values,
            marker="o",
            linewidth=1.3,
            label=texts.mn_legend.format(mn=label),
            clip_on=False,  # AB/2 = 1 m sits on the axis edge, as on bilog paper
        )
        segment_bars = bars.get(mn_m, [])
        _draw_error_bars(axes, segment_bars, line.get_color(), y_limits[0])
        reaching_zero = {bar.ab2_m for bar in segment_bars if bar.reaches_zero}
        for point, rho_a in zip(segment, rho_values, strict=True):
            if point.warnings or point.point.ab2_m in reaching_zero:
                flagged_ab2.append(point.point.ab2_m)
                flagged_rho.append(rho_a)
    if flagged_ab2:
        axes.scatter(
            flagged_ab2,
            flagged_rho,
            s=160,
            facecolors="none",
            edgecolors="tab:red",
            linewidths=1.5,
            label=texts.quality_warning,
            zorder=3,
            clip_on=False,
        )

    if all_bars:
        # An empty bar in a neutral colour stands for the bars of every segment in the legend.
        axes.errorbar(
            [], [], yerr=[], fmt="none", ecolor="0.35", capsize=3.0, label=texts.error_bars
        )

    axes.set_xscale("log")
    axes.set_yscale("log")
    axes.set_xlim(*x_limits)
    axes.set_ylim(*y_limits)
    axes.set_aspect("equal")
    axes.set_title(texts.title)
    axes.set_xlabel(texts.x_axis)
    axes.set_ylabel(texts.y_axis)
    axes.grid(visible=True, which="both", alpha=0.25, linewidth=0.7)
    axes.legend(loc="best", fontsize="small")
    return figure
