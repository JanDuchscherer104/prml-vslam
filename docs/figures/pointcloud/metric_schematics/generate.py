from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

OUT_DIR = Path(__file__).resolve().parent

REF_COLOR = "#2b6cb0"
EST_COLOR = "#e76f51"
ACC_COLOR = "#9b2c2c"
COMP_COLOR = "#4f7dd6"
GOOD_COLOR = "#2f9e6d"
MISS_COLOR = "#c94f4f"
MUTED = "#5f6773"
LIGHT = "#f7f9fc"

REFERENCE = np.array(
    [
        [0.8, 1.0],
        [1.5, 1.35],
        [2.2, 1.15],
        [2.9, 1.45],
        [3.6, 1.25],
        [4.3, 1.55],
        [5.0, 1.35],
        [5.7, 1.65],
    ],
    dtype=float,
)

ESTIMATE = np.array(
    [
        [0.9, 0.82],
        [1.45, 1.58],
        [2.8, 1.18],
        [3.45, 1.65],
    ],
    dtype=float,
)


def nearest_segments(
    source: np.ndarray, target: np.ndarray
) -> tuple[list[tuple[tuple[float, float], tuple[float, float]]], np.ndarray]:
    distances = np.linalg.norm(source[:, None, :] - target[None, :, :], axis=2)
    nearest = distances.argmin(axis=1)
    segments = [(tuple(point), tuple(target[index])) for point, index in zip(source, nearest, strict=True)]
    return segments, distances[np.arange(len(source)), nearest]


def base_figure(width: float = 7.0, height: float = 3.7):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(0.25, 6.45)
    ax.set_ylim(0.15, 2.75)
    ax.axis("off")
    return fig, ax


def scatter_clouds(ax, *, reference_alpha: float = 1.0, estimate_alpha: float = 1.0) -> None:
    ax.scatter(
        REFERENCE[:, 0],
        REFERENCE[:, 1],
        s=90,
        c=REF_COLOR,
        edgecolors="white",
        linewidths=1.2,
        alpha=reference_alpha,
        label="reference cloud R",
        zorder=3,
    )
    ax.scatter(
        ESTIMATE[:, 0],
        ESTIMATE[:, 1],
        s=105,
        marker="s",
        c=EST_COLOR,
        edgecolors="white",
        linewidths=1.2,
        alpha=estimate_alpha,
        label="estimate cloud E",
        zorder=4,
    )


def add_segments(ax, segments, *, color: str, label: str) -> None:
    collection = LineCollection(segments, colors=color, linewidths=2.0, alpha=0.88, zorder=2)
    ax.add_collection(collection)
    for start, end in segments:
        arrow = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=0,
            color=color,
            alpha=0.88,
            zorder=2,
        )
        ax.add_patch(arrow)
    ax.text(0.55, 2.55, label, color=color, fontsize=12, fontweight="bold", va="center")


def add_legend(ax) -> None:
    ax.add_patch(Rectangle((4.35, 2.04), 1.72, 0.46, facecolor="white", edgecolor="#d9dee8", linewidth=0.8, alpha=0.92))
    ax.scatter([4.52], [2.36], s=72, c=REF_COLOR, edgecolors="white", linewidths=1.0, zorder=5)
    ax.text(4.68, 2.36, "reference R", fontsize=8.8, va="center", color=MUTED)
    ax.scatter([4.52], [2.16], s=78, marker="s", c=EST_COLOR, edgecolors="white", linewidths=1.0, zorder=5)
    ax.text(4.68, 2.16, "estimate E", fontsize=8.8, va="center", color=MUTED)


def save(fig, name: str) -> None:
    fig.savefig(OUT_DIR / name, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)


def accuracy() -> None:
    fig, ax = base_figure()
    segments, _ = nearest_segments(ESTIMATE, REFERENCE)
    scatter_clouds(ax)
    add_segments(ax, segments, color=ACC_COLOR, label="accuracy: estimate -> nearest reference")
    ax.text(0.55, 0.28, "average these E -> R distances", fontsize=10.5, color=MUTED, va="center")
    add_legend(ax)
    save(fig, "pointcloud_accuracy.svg")


def completeness() -> None:
    fig, ax = base_figure()
    segments, distances = nearest_segments(REFERENCE, ESTIMATE)
    scatter_clouds(ax)
    add_segments(ax, segments, color=COMP_COLOR, label="completeness: reference -> nearest estimate")
    far = distances > 0.7
    ax.scatter(
        REFERENCE[far, 0], REFERENCE[far, 1], s=155, facecolors="none", edgecolors=MISS_COLOR, linewidths=2.2, zorder=5
    )
    ax.add_patch(Rectangle((4.72, 0.66), 1.33, 1.35, fill=False, linestyle="--", linewidth=1.8, edgecolor=MISS_COLOR))
    ax.text(4.78, 0.43, "uncovered reference region", fontsize=9.2, color=MISS_COLOR, va="center")
    ax.text(0.55, 0.28, "long R -> E distances indicate missing surface", fontsize=10.5, color=MUTED, va="center")
    add_legend(ax)
    save(fig, "pointcloud_completeness.svg")


def chamfer() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.9, 3.45), gridspec_kw={"width_ratios": [1.18, 0.82]})
    left, right = axes
    for ax in axes:
        ax.axis("off")
    left.set_aspect("equal", adjustable="box")
    left.set_xlim(0.25, 6.45)
    left.set_ylim(0.15, 2.75)

    acc_segments, _ = nearest_segments(ESTIMATE, REFERENCE)
    comp_segments, _ = nearest_segments(REFERENCE, ESTIMATE)
    scatter_clouds(left, reference_alpha=0.94, estimate_alpha=0.94)
    left.add_collection(LineCollection(acc_segments, colors=ACC_COLOR, linewidths=1.8, alpha=0.7, zorder=2))
    left.add_collection(
        LineCollection(comp_segments, colors=COMP_COLOR, linewidths=1.8, alpha=0.58, linestyles="dashed", zorder=1)
    )
    left.text(0.55, 2.55, "Chamfer = both nearest-neighbor directions", fontsize=12, fontweight="bold", color=MUTED)
    left.text(0.55, 0.28, "red: E -> R accuracy    blue dashed: R -> E completeness", fontsize=9.7, color=MUTED)

    right.set_xlim(0, 1)
    right.set_ylim(0, 1)
    right.text(0.03, 0.92, "Same total, different failure", fontsize=12, fontweight="bold", color=MUTED)
    examples = [
        ("balanced", 0.18, 0.18, 0.64),
        ("incomplete", 0.03, 0.33, 0.32),
    ]
    for label, acc, comp, y in examples:
        total = acc + comp
        right.text(0.05, y + 0.055, label, fontsize=10.5, color=MUTED, va="center")
        x0, width = 0.32, 0.47
        acc_width = width * acc / total
        comp_width = width * comp / total
        right.add_patch(Rectangle((x0, y), acc_width, 0.07, color=ACC_COLOR, ec="none"))
        right.add_patch(Rectangle((x0 + acc_width, y), comp_width, 0.07, color=COMP_COLOR, ec="none"))
        right.text(0.83, y + 0.035, "0.36 m", fontsize=9.5, color=MUTED, va="center")
    right.text(0.32, 0.13, "accuracy", fontsize=9.5, color=ACC_COLOR, fontweight="bold")
    right.text(0.58, 0.13, "+ completeness", fontsize=9.5, color=COMP_COLOR, fontweight="bold")
    save(fig, "pointcloud_chamfer.svg")


def f1() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.25), gridspec_kw={"width_ratios": [1.0, 1.0]})
    for ax in axes:
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(0.2, 3.6)
        ax.set_ylim(0.2, 2.6)
        ax.axis("off")

    precision_ax, recall_ax = axes
    tau = 0.38
    estimate_points = np.array([[0.9, 1.65], [1.9, 1.2], [2.9, 1.75]])
    reference_points = np.array([[1.05, 1.82], [2.05, 1.33], [3.55, 2.18]])
    for point in estimate_points:
        precision_ax.add_patch(Circle(point, tau, facecolor="#fff0f0", edgecolor=EST_COLOR, linewidth=1.5, alpha=0.85))
    precision_ax.scatter(
        estimate_points[:, 0],
        estimate_points[:, 1],
        s=105,
        marker="s",
        c=EST_COLOR,
        edgecolors="white",
        linewidths=1.1,
        zorder=3,
    )
    precision_ax.scatter(
        reference_points[:, 0], reference_points[:, 1], s=90, c=REF_COLOR, edgecolors="white", linewidths=1.1, zorder=4
    )
    precision_ax.text(0.35, 2.42, "precision", fontsize=13, fontweight="bold", color=MUTED)
    precision_ax.text(
        0.35, 0.38, "estimate point counts as hit\nif reference lies within 5 cm", fontsize=9.5, color=MUTED
    )
    precision_ax.text(2.8, 0.55, "miss", fontsize=10, color=MISS_COLOR, fontweight="bold")
    precision_ax.text(0.95, 2.2, "hit", fontsize=10, color=GOOD_COLOR, fontweight="bold")

    estimate_points = np.array([[0.9, 1.65], [2.0, 1.2]])
    reference_points = np.array([[1.05, 1.82], [2.05, 1.33], [3.0, 2.0]])
    for point in reference_points:
        recall_ax.add_patch(Circle(point, tau, facecolor="#eaf2ff", edgecolor=REF_COLOR, linewidth=1.5, alpha=0.85))
    recall_ax.scatter(
        estimate_points[:, 0],
        estimate_points[:, 1],
        s=105,
        marker="s",
        c=EST_COLOR,
        edgecolors="white",
        linewidths=1.1,
        zorder=3,
    )
    recall_ax.scatter(
        reference_points[:, 0], reference_points[:, 1], s=90, c=REF_COLOR, edgecolors="white", linewidths=1.1, zorder=4
    )
    recall_ax.text(0.35, 2.42, "recall", fontsize=13, fontweight="bold", color=MUTED)
    recall_ax.text(
        0.35, 0.38, "reference point counts as covered\nif estimate lies within 5 cm", fontsize=9.5, color=MUTED
    )
    recall_ax.text(2.75, 2.42, "uncovered", fontsize=10, color=MISS_COLOR, fontweight="bold")
    recall_ax.text(0.95, 2.2, "covered", fontsize=10, color=GOOD_COLOR, fontweight="bold")

    save(fig, "pointcloud_f1.svg")


def main() -> None:
    accuracy()
    completeness()
    chamfer()
    f1()


if __name__ == "__main__":
    main()
