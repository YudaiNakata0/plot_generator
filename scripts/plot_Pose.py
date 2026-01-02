#!/usr/bin/env python3
import rosbag
import numpy as np
import matplotlib.pyplot as plt
from geometry_msgs.msg import Pose, PoseStamped
import argparse
import os

def plot_Pose(file_name, topic_name, tx=None, ty=None, tz=None, rx=None, ry=None, rz=None, start_time=None, end_time=None, ox=None, oy=None, oz=None):
    # path conversion
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    # open bag file
    bag = rosbag.Bag(file_path)

    # initialize
    time = []
    x = []
    y = []
    z = []

    # read data
    for topic, msg, t in bag.read_messages(topics=[topic_name]):
        time.append(t.to_sec())
        x.append(msg.position.x)
        y.append(msg.position.y)
        z.append(msg.position.z)

    bag.close()

    # list -> numpy array
    time = np.array(time)
    x = np.array(x)
    y = np.array(y)
    z = np.array(z)

    # adjust time(start from 0)
    time -= time[0]

    # crop by time
    if start_time and end_time:
        start_time = float(start_time)
        end_time = float(end_time)
        mask = (time >= start_time) & (time <= end_time)
        time = time[mask]
        x = x[mask]
        y = y[mask]
        z = z[mask]
        time -= time[0]

    # graph
    fig_number = 3 - int(ox is not None) - int(oy is not None) - int(oz is not None)
    print(fig_number)
    fig, ax = plt.subplots(fig_number, 1, sharex=True, figsize=(8, 3*fig_number))

    # x
    if not ox:
        if fig_number > 1:
            ax[0].plot(time, x, label="x")
            # visualize target range
            if tx:
                tx = float(tx)
                ax[0].axhline(tx, color="C1", alpha=0.5)
                if rx:
                    rx = float(rx)
                    ax[0].axhspan(tx-rx, tx+rx, color="C1", alpha=0.2)
            ax[0].set_ylabel("x [m]")
            ax[0].set_xlabel("Time [s]")
            ax[0].legend()
        elif fig_number == 1:
            ax.plot(time, x, label="x")
            if tx:
                tx = float(tx)
                ax.axhline(tx, color="C1", alpha=0.5)
                if rx:
                    rx = float(rx)
                    ax.axhspan(tx-rx, tx+rx, color="C1", alpha=0.2)
            ax.set_ylabel("x [m]")
            ax.set_xlabel("Time [s]")
            ax.legend()

    # y
    if not oy:
        if fig_number > 1:
            ax[1].plot(time, y, label="y")
            if ty:
                ty = float(ty)
                ax[1].axhline(ty, color="C1", alpha=0.5)
                if ry:
                    ry = float(ry)
                    ax[1].axhspan(ty-ry, ty+ry, color="C1", alpha=0.2)
            ax[1].set_ylabel("y [m]")
            ax[1].set_xlabel("Time [s]")
            ax[1].legend()
        elif fig_number == 1:
            ax.plot(time, y, label="y")
            if ty:
                ty = float(ty)
                ax.axhline(ty, color="C1", alpha=0.5)
                if ry:
                    ry = float(ry)
                    ax.axhspan(ty-ry, ty+ry, color="C1", alpha=0.2)
            ax.set_ylabel("y [m]")
            ax.set_xlabel("Time [s]")
            ax.legend()

    # z
    if not oz:
        if fig_number > 1:
            ax[2].plot(time, z, label="z")
            if tz:
                tz = float(tz)
                ax[2].axhline(tz, color="C1", alpha=0.5)
                if rz:
                    rz = float(rz)
                    ax[2].axhspan(tz-rz, tz+rz, color="C1", alpha=0.2)
            ax[2].set_ylabel("z [m]")
            ax[2].set_xlabel("Time [s]")
            ax[2].legend()
        elif fig_number == 1:
            ax.plot(time, z, label="z")
            if tz:
                tz = float(tz)
                ax.axhline(tz, color="C1", alpha=0.5)
                if rz:
                    rz = float(rz)
                    ax[2].axhspan(tz-rz, tz+rz, color="C1", alpha=0.2)
            ax.set_ylabel("z [m]")
            ax.set_xlabel("Time [s]")
            ax.legend()            

    plt.tight_layout()
    plt.show()    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="rosbag file")
    parser.add_argument("topic_name", help="topic name(Pose type)")
    parser.add_argument("-x", "--target_x", help="target x position")
    parser.add_argument("-y", "--target_y", help="target y position")
    parser.add_argument("-z", "--target_z", help="target z position")
    parser.add_argument("--rx", help="target x range([x-rx, x+rx])")
    parser.add_argument("--ry", help="target y range([y-ry, y+ry])")
    parser.add_argument("--rz", help="target z range([z-rz, z+rz])")
    parser.add_argument("-s", "--start_time",  help="start time")
    parser.add_argument("-e", "--end_time", help="end time")
    parser.add_argument("--ox", help="off x plot")
    parser.add_argument("--oy", help="off y plot")
    parser.add_argument("--oz", help="off z plot")
    args = parser.parse_args()
    file_name = args.file_name
    topic_name = args.topic_name
    x = args.target_x
    y = args.target_y
    z = args.target_z
    rx = args.rx
    ry = args.ry
    rz = args.rz
    s = args.start_time
    e = args.end_time
    ox = args.ox
    oy = args.oy
    oz = args.oz
    plot_Pose(file_name, topic_name, x, y, z, rx, ry, rz, s, e, ox, oy, oz)
