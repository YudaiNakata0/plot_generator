#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os

def main(npz_files, output, show):
    theta_data = []
    labels = []

    color = "#00ffff"

    for f in npz_files:
        data = np.load(f)
        if "theta" not in data:
            raise KeyError(f"{f} does not contain key 'theta'")

        theta = data["theta"]
        theta_data.append(theta)

        labels.append(os.path.basename(f))

    # ===== boxplot =====
    fig, ax = plt.subplots(figsize=(1.8 * len(theta_data), 5))

    bp = ax.boxplot(
        theta_data,
        whis=[0, 100],
        vert=True,
        showfliers=True,
        patch_artist=True,
        boxprops=dict(linewidth=1.2, edgecolor="black"),
        medianprops=dict(linewidth=1.0, color="black"),
        whiskerprops=dict(linewidth=1.2, color="black"),
        capprops=dict(linewidth=1.2, color="black"),
    )

    for i, box in enumerate(bp["boxes"]):
        box.set_facecolor(color)
        box.set_edgecolor("black")

    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Orientation Error theta [rad]")
    ax.set_title("Oritentation Error Distribution per Experiment")
    ax.set_ylim(bottom=0)

    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=300)
        print(f"saved: {output}")

    if show:
        plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create boxplots from r in multiple npz files"
    )
    parser.add_argument(
        "npz_files",
        nargs="+",
        help="npz files containing r array"
    )
    parser.add_argument(
        "-o", "--output",
        help="output image file (e.g. boxplot.png)"
    )
    parser.add_argument(
        "--noshow",
        action="store_true",
        help="do not display the figure"
    )

    args = parser.parse_args()

    main(
        args.npz_files,
        args.output,
        show=not args.noshow
    )
