#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os

def main(npz_files, output, show):
    r_data = []
    p_data = []
    y_data = []
    labels = []
    box_data = []
    positions = []
    xtick_positions = []
    xtick_labels = []

    colors = ["#00ffff", "#00ff00", "#ff0099"]  # Roll, Pitch, Yaw

    for f in npz_files:
        data = np.load(f)

        r = data["roll"]
        p = data["pitch"]
        y = data["yaw"]
        r_data.append(r)
        p_data.append(p)
        y_data.append(y)

        labels.append(os.path.basename(f))

        pos = 1
        gap_a = 0.5
        gap_b = 0.4

        for label, r, p, y in zip(labels, r_data, p_data, y_data):
            # Roll, Pitch, Yaw を順に追加
            box_data.extend([r, p, y])
            positions.extend([pos, pos + gap_a, pos + gap_a*2])

            # xtick は experiment の中央に置く
            xtick_positions.append(pos + 1)
            xtick_labels.append(label)

            pos += gap_a*3 + gap_b

    # ===== boxplot =====
    fig, ax = plt.subplots(figsize=(1.8 * len(labels)*3, 5))

    bp = ax.boxplot(
        box_data,
        positions=positions,
        widths=0.4,
        whis=[0, 100],
        showfliers=True,
        patch_artist=True,
        boxprops=dict(linewidth=1.0, edgecolor="black"),
        medianprops=dict(linewidth=0.6, color="black"),
        whiskerprops=dict(linewidth=1.0, color="black"),
        capprops=dict(linewidth=1.0, color="black"),
    )

    for i, box in enumerate(bp["boxes"]):
        box.set_facecolor(colors[i % 3])
        box.set_edgecolor("black")
    ax.set_xticks(xtick_positions)
    ax.set_xticklabels(xtick_labels, rotation=30, ha="right")

    ax.set_ylabel("Orientation Error [rad]")
    ax.set_title("Orientation Error Distribution per Experiment")

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
