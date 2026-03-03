#!/usr/bin/env python3
import rosbag
import numpy as np
import matplotlib.pyplot as plt
from geometry_msgs.msg import Pose, PoseStamped
import argparse
import os
from module import operation_quaternion as oq

def plot_Pose(file_name, topic_name, tx=None, ty=None, tz=None, rx=None, ry=None, rz=None, troll=None, tpitch=None, tyaw=None, start_time=None, end_time=None, ox=None, oy=None, oz=None):
    # path conversion
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    # open bag file
    bag = rosbag.Bag(file_path)

    # initialize
    time = []
    x = []
    y = []
    z = []
    roll = []
    pitch = []
    yaw = []

    # target pose
    if tx:
        tx = float(tx)
    else:
        tx = 0
    if ty:
        ty = float(ty)
    else:
        ty = 0
    if tz:
        tz = float(tz)
    else:
        tz = 0
    if troll:
        troll = float(troll)
    else:
        troll = 0
    if tpitch:
        tpitch = float(tpitch)
    else:
        tpitch = 0
    if tyaw:
        tyaw = float(tyaw)
    else:
        tyaw = 0

    # read data
    for topic, msg, t in bag.read_messages(topics=[topic_name]):
        time.append(t.to_sec())
        x.append(msg.position.x)
        y.append(msg.position.y)
        z.append(msg.position.z)
        q = msg.orientation
        qr, qp, qy = oq.quaternion_to_euler(q)
        roll.append(qr)
        pitch.append(qp)
        yaw.append(qy)

    bag.close()

    # list -> numpy array
    time = np.array(time)
    x = np.array(x)
    y = np.array(y)
    z = np.array(z)
    roll = np.array(roll)
    pitch = np.array(pitch)
    yaw = np.array(yaw)

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
        roll = roll[mask]
        pitch = pitch[mask]
        yaw = yaw[mask]
        time -= time[0]

    # save xyz data
    if start_time and end_time:
        name = "data/endeffector_pose_" + "[" + str(round(start_time)) + "-" + str(round(end_time)) + "]" + file_name + ".npz"
    else:
        name = "data/endeffector_pose_" + file_name + ".npz"
    name = name.replace("bags/", "")
    name = name.replace(".bag", "")
    np.savez(name, time=time, x=x, y=y, z=z, tx=tx, ty=ty, tz=tz, roll=roll, pitch=pitch, yaw=yaw, troll=troll, tpitch=tpitch, tyaw=tyaw)

    # graph
    fig_number = 3 - int(ox is not None) - int(oy is not None) - int(oz is not None)
    print(fig_number)
    fig, ax = plt.subplots(fig_number, 1, sharex=True, figsize=(8, 3*fig_number))

    # range
    if oy and oz:
        display_range = (x.max()-x.min()) * 0.5 + 0.001
    else:
        display_range = np.array([x.max()-x.min(), y.max()-y.min(), z.max()-z.min()]).max() * 0.5 + 0.001
    mx = (x.max()+x.min()) * 0.5
    my = (y.max()+y.min()) * 0.5
    mz = (z.max()+z.min()) * 0.5
    thres = 0.03
    if display_range < thres:
        display_range = thres

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
            ax[0].set_ylim(mx - display_range, mx + display_range)
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
            ax.set_ylim(mx - display_range, mx + display_range)

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
            ax[1].set_ylim(my - display_range, my + display_range)
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
            ax.set_ylim(my - display_range, my + display_range)

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
            ax[2].set_ylim(mz - display_range, mz + display_range)
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
            ax.set_ylim(mz - display_range, mz + display_range)

    plt.tight_layout()
    plt.show()    

    # rpy
    fig_rpy, ax_rpy = plt.subplots(3, 1, sharex=True, figsize=(8, 9))

    ax_rpy[0].plot(time, roll, label="roll")
    if troll:
        ax_rpy[0].axhline(troll, color="C1", alpha=0.5)
    ax_rpy[0].set_ylabel("Roll [rad]")
    ax_rpy[0].legend()

    ax_rpy[1].plot(time, pitch, label="pitch")
    if tpitch:
        ax_rpy[1].axhline(tpitch, color="C1", alpha=0.5)
    ax_rpy[1].set_ylabel("Pitch [rad]")
    ax_rpy[1].legend()

    ax_rpy[2].plot(time, yaw, label="yaw")
    if tyaw:
        ax_rpy[2].axhline(tyaw, color="C1", alpha=0.5)
    ax_rpy[2].set_ylabel("Yaw [rad]")
    ax_rpy[2].set_xlabel("Time [s]")
    ax_rpy[2].legend()

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
    parser.add_argument("--roll", help="target roll")
    parser.add_argument("--pitch", help="target pitch")
    parser.add_argument("--yaw", help="target yaw")
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
    roll = args.roll
    pitch = args.pitch
    yaw = args.yaw
    s = args.start_time
    e = args.end_time
    ox = args.ox
    oy = args.oy
    oz = args.oz
    plot_Pose(file_name, topic_name, x, y, z, rx, ry, rz, roll, pitch, yaw, s, e, ox, oy, oz)
