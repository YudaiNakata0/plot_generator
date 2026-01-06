#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import os
import argparse

def plot_from_npz(file_name):
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    data = np.load(file_path)
    time = data["time"]
    x = data["x"]
    y = data["y"]
    z = data["z"]
    # plt.rcParams.update({
    #     "font.size": 14,
    #     "axes.grid": True,
    #     "grid.linestyle": "--",
    #     "grid.alpha": 0.5,
    #     "lines.linewidth": 2,
    #     "legend.frameon": False,
    # })

    fig, ax = plt.subplots(3, 1, sharex=True, figsize=(8, 8))

    ax[0].plot(time, x, label="x")
    ax[0].set_ylabel("x [m]")
    ax[0].legend()

    ax[1].plot(time, y, label="y")
    ax[1].set_ylabel("y [m]")
    ax[1].legend()

    ax[2].plot(time, z, label="z")
    ax[2].set_ylabel("z [m]")
    ax[2].set_xlabel("Time [s]")
    ax[2].legend()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="npz file")
    args = parser.parse_args()
    file_name = args.file_name
    plot_from_npz(file_name)
