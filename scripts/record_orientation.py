#!/usr/bin/env python3
import rosbag
import numpy as np
import matplotlib.pyplot as plt
from geometry_msgs.msg import Pose, PoseStamped
import argparse
import os
from module import operation_quaternion as oq

def record_orientation(file_name, topic_name, troll=None, tpitch=None, tyaw=None, start_time=None, end_time=None):
    # path conversion
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    # open bag file
    bag = rosbag.Bag(file_path)

    # initialize
    time = []
    theta = []

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

    # target quatrenion
    tq = oq.euler_to_quaternion([troll, tpitch, tyaw])

    # read data
    for topic, msg, t in bag.read_messages(topics=[topic_name]):
        time.append(t.to_sec())
        q = msg.orientation
        dq = oq.inverse_calculate_quaternion(q, tq)
        dtheta = 2 * np.arccos(dq.w)
        theta.append(dtheta)

    bag.close()

    # list -> numpy array
    time = np.array(time)
    theta = np.array(theta)

    # adjust time(start from 0)
    time -= time[0]

    # crop by time
    if start_time and end_time:
        start_time = float(start_time)
        end_time = float(end_time)
        mask = (time >= start_time) & (time <= end_time)
        time = time[mask]
        theta = theta[mask]
        time -= time[0]

    # save xyz data
    if start_time and end_time:
        name = "data/endeffector_orientation_error_" + "[" + str(round(start_time)) + "-" + str(round(end_time)) + "]" + file_name + ".npz"
    else:
        name = "data/endeffector_orientation_error_" + file_name + ".npz"
    name = name.replace("bags/", "")
    name = name.replace(".bag", "")
    np.savez(name, time=time, theta=theta)

    # plot
    fig, ax = plt.subplots(1, 1, sharex=True, figsize=(8, 3))

    ax.plot(time, theta, label="orientatio error")
    ax.set_ylabel("Orientation error [rad]")
    ax.set_xlabel("Time [s]")
    ax.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="rosbag file")
    parser.add_argument("topic_name", help="topic name(Pose type)")
    parser.add_argument("-r", "--roll", help="target roll")
    parser.add_argument("-p", "--pitch", help="target pitch")
    parser.add_argument("-y", "--yaw", help="target yaw")
    parser.add_argument("-s", "--start_time",  help="start time")
    parser.add_argument("-e", "--end_time", help="end time")
    args = parser.parse_args()
    file_name = args.file_name
    topic_name = args.topic_name
    r = args.roll
    p = args.pitch
    y = args.yaw
    s = args.start_time
    e = args.end_time
    record_orientation(file_name, topic_name, r, p, y, s, e)
