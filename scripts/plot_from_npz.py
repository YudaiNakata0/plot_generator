#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import os
import argparse

def plot_from_npz(file_name, rx, ry, rz):
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    data = np.load(file_path)
    time = data["time"]
    x = data["x"]
    y = data["y"]
    z = data["z"]
    tx = data["tx"]
    ty = data["ty"]
    tz = data["tz"]
    # plt.rcParams.update({
    #     "font.size": 14,
    #     "axes.grid": True,
    #     "grid.linestyle": "--",
    #     "grid.alpha": 0.5,
    #     "lines.linewidth": 2,
    #     "legend.frameon": False,
    # })

    display_range = 0.03
    mx = (x.max()+x.min()) * 0.5
    my = (y.max()+y.min()) * 0.5
    mz = (z.max()+z.min()) * 0.5

    fig, ax = plt.subplots(3, 1, sharex=True, figsize=(8, 8))

    ax[0].plot(time, x, label="x")
    ax[0].axhline(tx, color="C1", alpha=0.5)
    if rx:
        rx = float(rx)
        ax[0].axhspan(tx-rx, tx+rx, color="C1", alpha=0.2)
    ax[0].set_ylabel("x [m]")
    ax[0].set_xlabel("Time [s]")
    ax[0].legend()
    ax[0].set_ylim(mx - display_range, mx + display_range)

    ax[1].plot(time, y, label="y")
    ax[1].axhline(ty, color="C1", alpha=0.5)
    if ry:
        ry = float(ry)
        ax[1].axhspan(ty-ry, ty+ry, color="C1", alpha=0.2)
    ax[1].set_ylabel("y [m]")
    ax[1].set_xlabel("Time [s]")
    ax[1].legend()
    ax[1].set_ylim(my - display_range, my + display_range)

    ax[2].plot(time, z, label="z")
    ax[2].axhline(tz, color="C1", alpha=0.5)
    if rz:
        rz = float(rz)
        ax[2].axhspan(tz-rz, tz+rz, color="C1", alpha=0.2)
    ax[2].set_ylabel("z [m]")
    ax[2].set_xlabel("Time [s]")
    ax[2].legend()
    ax[2].set_ylim(mz - display_range, mz + display_range)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="npz file")
    parser.add_argument("--rx", help="target range(x)")
    parser.add_argument("--ry", help="target range(y)")
    parser.add_argument("--rz", help="target range(z)")
    args = parser.parse_args()
    file_name = args.file_name
    rx = args.rx
    ry = args.ry
    rz = args.rz
    plot_from_npz(file_name, rx, ry, rz)
