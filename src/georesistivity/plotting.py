"""Preparation and Matplotlib rendering for spacing-based plots."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from matplotlib.figure import Figure

from georesistivity.models import MeasurementResult

PlotScale = Literal["linear", "log-log"]


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
    axes.set_title("Apparent Resistivity vs. Electrode Spacing")
    axes.set_xlabel("AB/2 [m]")
    axes.set_ylabel("Apparent resistivity [\u03a9\u00b7m]")
    if scale == "log-log":
        axes.set_xscale("log")
        axes.set_yscale("log")
    axes.grid(visible=True, which="both", alpha=0.25, linewidth=0.7)
    return figure
