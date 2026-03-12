#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os


def main(r_files, theta_files, output, show):

    if len(r_files) != len(theta_files):
        raise ValueError("number of r files and theta files must match")

    r_data = []
    theta_data = []
    labels = []

    for rf, tf in zip(r_files, theta_files):

        r_npz = np.load(rf)
        th_npz = np.load(tf)

        if "r" not in r_npz:
            raise KeyError(f"{rf} does not contain key 'r'")
        if "theta" not in th_npz:
            raise KeyError(f"{tf} does not contain key 'theta'")

        r_data.append(r_npz["r"])
        theta_data.append(th_npz["theta"])

        labels.append(os.path.basename(rf).replace(".npz",""))

    n = len(r_data)

    # ===== figure =====
    fig, ax_r = plt.subplots(figsize=(2.2 * n, 5))
    ax_theta = ax_r.twinx()

    r_color = "#00ffff"
    theta_color = "#ff9999"

    r_positions = []
    theta_positions = []
    xticks = []

    space_r_theta = 0.8
    space_exp = 2.0
    for i in range(n):
        r_positions.append(space_exp*i + space_r_theta)
        theta_positions.append(space_exp*i + 2*space_r_theta)
        xticks.append(space_exp*i + 1.5*space_r_theta)

    # ===== r boxplot =====
    bp_r = ax_r.boxplot(
        r_data,
        positions=r_positions,
        widths=0.6,
        whis=[0,100],
        vert=True,
        showfliers=True,
        patch_artist=True,
        boxprops=dict(linewidth=1.2, edgecolor="black"),
        medianprops=dict(linewidth=1.0, color="black"),
        whiskerprops=dict(linewidth=1.2, color="black"),
        capprops=dict(linewidth=1.2, color="black"),
    )

    for box in bp_r["boxes"]:
        box.set_facecolor(r_color)

    # ===== theta boxplot =====
    bp_theta = ax_theta.boxplot(
        theta_data,
        positions=theta_positions,
        widths=0.6,
        whis=[0,100],
        vert=True,
        showfliers=True,
        patch_artist=True,
        boxprops=dict(linewidth=1.2, edgecolor="black"),
        medianprops=dict(linewidth=1.0, color="black"),
        whiskerprops=dict(linewidth=1.2, color="black"),
        capprops=dict(linewidth=1.2, color="black"),
    )

    for box in bp_theta["boxes"]:
        box.set_facecolor(theta_color)

    # ===== x axis =====
    ax_r.set_xticks(xticks)
    ax_r.set_xticklabels(labels, rotation=30, ha="right")

    # ===== labels =====
    ax_r.set_ylabel("Position Error r [m]")
    ax_theta.set_ylabel("Orientation Error θ [rad]")

    ax_r.set_ylim(bottom=0)
    ax_theta.set_ylim(bottom=0)
    # 左軸範囲
    ymin, ymax = ax_r.get_ylim()

    # 右軸を同じスケールにする
    ax_theta.set_ylim(ymin, ymax)

    # ===== grid =====
    ax_r.grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=300)
        print(f"saved: {output}")

    if show:
        plt.show()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Create paired boxplots for r and theta"
    )

    parser.add_argument(
        "--r",
        nargs="+",
        required=True,
        help="npz files containing r"
    )

    parser.add_argument(
        "--theta",
        nargs="+",
        required=True,
        help="npz files containing theta"
    )

    parser.add_argument(
        "-o", "--output",
        help="output image file"
    )

    parser.add_argument(
        "--noshow",
        action="store_true"
    )

    args = parser.parse_args()

    main(
        args.r,
        args.theta,
        args.output,
        show=not args.noshow
    )
