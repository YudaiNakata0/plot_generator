#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from geometry_msgs.msg import Pose, PoseStamped
import argparse
import os
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from matplotlib.ticker import MaxNLocator
from matplotlib import patches

def draw_2D_trajectory(file_name, r, angled, axis):
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))

    # read data from npz file
    data = np.load(file_path)
    time = data["time"]
    x = data["x"]
    y = data["y"]
    z = data["z"]
    tx = data["tx"]
    ty = data["ty"]
    tz = data["tz"]

    # adjust for LineCollection
    if axis == "x":
        points = np.array([y, z]).T.reshape(-1, 1, 2)
    elif axis == "y":
        points = np.array([x, z]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # color map
    norm = plt.Normalize(time.min(), time.max())
    lc = LineCollection(segments, cmap="viridis", norm=norm)
    lc.set_array(time)
    lc.set_linewidth(2.0)

    # make figure
    fig, ax = plt.subplots(figsize=(6, 6))

    # trajectory
    ax.add_collection(lc)

    if axis == "x":
        # target area
        if ty and tz and r:
            ty = float(ty)
            tz = float(tz)
            r = float(r)

            if angled:
                target_circle = patches.Ellipse((ty, tz), 2*r, 2*r*np.cos(0.2), color="C1", alpha=0.2, label="target area")
            else:
                target_circle = Circle((ty, tz), r, color="C1", alpha=0.2, label="target area")
            ax.add_patch(target_circle)

        # start and end
        ax.scatter(y[0], z[0], marker="o", color="black", label="start")
        ax.scatter(y[-1], z[-1], marker="x", color="black", label="end")

        ax.set_xlabel("y [m]")
        ax.set_ylabel("z [m]")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True)

        # color bar
        cbar = plt.colorbar(lc, ax=ax)
        cbar.set_label("Time [s]")

        ax.legend()
        plt.tight_layout()

        display_range = np.array([y.max()-y.min(), z.max()-z.min()]).max() * 0.5 + 0.004
        mx = (x.max()+x.min()) * 0.5
        my = (y.max()+y.min()) * 0.5
        mz = (z.max()+z.min()) * 0.5
        ax.set_xlim(my - display_range, my + display_range)
        ax.set_ylim(mz - display_range, mz + display_range)
        plt.gca().invert_xaxis()
        plt.show()

    elif axis == "y":
        # target area
        if tx and tz and r:
            tx = float(tx)
            tz = float(tz)
            r = float(r)

            if angled:
                plt.plot([tx+np.sin(0.2)*r, tx-np.sin(0.2)*r], [tz-np.cos(0.2)*r, tz+np.cos(0.2)*r], color="C1", alpha=0.2, label="target_area")
            else:
                plt.plot([tx, tx], [tz-r, tz+r], color="C1", alpha=0.2, label="target_area")

        # start and end
        ax.scatter(x[0], z[0], marker="o", color="black", label="start")
        ax.scatter(x[-1], z[-1], marker="x", color="black", label="end")

        ax.set_xlabel("x [m]")
        ax.set_ylabel("z [m]")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True)

        # color bar
        cbar = plt.colorbar(lc, ax=ax)
        cbar.set_label("Time [s]")

        ax.legend()
        plt.tight_layout()

        # display range
        # display_range = np.array([x.max()-x.min(), z.max()-z.min()]).max() * 0.5 + 0.001
        display_range = (x.max()-x.min()) * 0.5 + 0.005
        mx = (x.max()+x.min()) * 0.5
        my = (y.max()+y.min()) * 0.5
        mz = (z.max()+z.min()) * 0.5
        if y.max() - y.min() > 0.1:
            display_range = 0.02
        ax.set_xlim(mx - display_range, mx + display_range)
        # ax.set_ylim(mz - display_range, mz + display_range)
        ax.set_aspect("equal", adjustable="box")
        plt.show()

def draw_3D_trajectory(file_name, r, angled):
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))

    # read data from npz file
    data = np.load(file_path)
    time = data["time"]
    x = data["x"]
    y = data["y"]
    z = data["z"]
    tx = data["tx"]
    ty = data["ty"]
    tz = data["tz"]

    # adjust for Line3DCollection
    points = np.array([x, y, z]).T.reshape(-1, 1, 3)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # color map
    norm = plt.Normalize(time.min(), time.max())
    lc = Line3DCollection(segments, cmap="viridis", norm=norm, linewidth=2.0)
    lc.set_array(time[:-1])

    # make figure
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection(lc)

    # start and end
    ax.scatter(x[0], y[0], z[0], color="black", marker="o", label="start")
    ax.scatter(x[-1], y[-1], z[-1], color="black", marker="x", label="end")

    # target area
    if tx and ty and tz and r:
        tx = float(tx)
        ty = float(ty)
        tz = float(tz)
        r = float(r)

        # target area on yz-plane
        theta = np.linspace(0, 2*np.pi, 60)
        radius = np.linspace(0, r, 30)
        Theta, R = np.meshgrid(theta, radius)
        y_disk = ty + R * np.cos(Theta)
        z_disk = tz + R * np.sin(Theta)
        # place the circle at x = target x
        x_disk = np.full_like(y_disk, tx)

        if angled:
            points = np.stack([x_disk-tx, y_disk-ty, z_disk-tz], axis=-1)
            rot = np.array([[np.cos(-0.2), 0, np.sin(-0.2)],
                            [0, 1, 0],
                            [-np.sin(-0.2), 0, np.cos(-0.2)]])
            points = points @ rot.T
            x_disk = points[..., 0] + tx
            y_disk = points[..., 1] + ty
            z_disk = points[..., 2] + tz

        ax.plot_surface(x_disk, y_disk, z_disk, color="C1", alpha=0.2, linewidth=0, shade=False)

    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_zlabel("z [m]")

    ax.xaxis.set_major_locator(MaxNLocator(5))
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.zaxis.set_major_locator(MaxNLocator(5))

    # color bar
    cbar = plt.colorbar(lc, ax=ax)
    cbar.set_label("Time [s]")

    ax.legend()
    plt.tight_layout()

    # display range
    display_range = np.array([x.max()-x.min(), y.max()-y.min(), z.max()-z.min()]).max() * 0.5
    mx = (x.max()+x.min()) * 0.5
    my = (y.max()+y.min()) * 0.5
    mz = (z.max()+z.min()) * 0.5
    ax.set_xlim(mx - display_range, mx + display_range)
    ax.set_ylim(my - display_range, my + display_range)
    ax.set_zlim(mz - display_range, mz + display_range)
    ax.set_box_aspect([1, 1, 1])
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="rosbag file")
    parser.add_argument("-m", "--mode", help="trajectory generate mode(2:2D, 3:3D)")
    parser.add_argument("-x", "--target_x", help="target x position")
    parser.add_argument("-y", "--target_y", help="target y position")
    parser.add_argument("-z", "--target_z", help="target z position")
    parser.add_argument("-r", "--radius", help="target radius")
    parser.add_argument("-a", "--angled", help="angled wall flag")
    parser.add_argument("--axis", default="x", help="normal axis")
    args = parser.parse_args()
    file_name = args.file_name
    mode = args.mode
    if not mode:
        print("input mode value")
    mode = int(mode)
    x = args.target_x
    y = args.target_y
    z = args.target_z
    r = args.radius
    angled = args.angled
    axis = args.axis
    if mode == 2:
        draw_2D_trajectory(file_name, r, angled, axis)
    elif mode == 3:
        draw_3D_trajectory(file_name, r, angled)
    else:
        print("invalid mode")
