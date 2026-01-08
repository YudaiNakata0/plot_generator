#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from geometry_msgs.msg import Pose, PoseStamped
import argparse
import os

def calculate_error(file_name, mode=None):
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    if mode:
        mode = int(mode)

    #read data from npz file
    data = np.load(file_path)
    time = data["time"]
    x = data["x"]
    y = data["y"]
    z = data["z"]
    l = np.array([len(x), len(y), len(z)]).min()
    tx = data["tx"]
    ty = data["ty"]
    tz = data["tz"]

    if mode == 1:
        dx = np.std(x)
        dy = np.std(y)
        dz = np.std(z)

    else:
        if tx == None:
            tx = 0
        if ty == None:
            ty = 0
        if tz == None:
            tz = 0
        print("target", tx, ty, tz)
        tmp_x = 0
        tmp_y = 0
        tmp_z = 0
        for i in range(l):
            tmp_x += (x[i] - tx) ** 2
            tmp_y += (y[i] - ty) ** 2
            tmp_z += (z[i] - tz) ** 2
        dx = np.sqrt(tmp_x / l)
        dy = np.sqrt(tmp_y / l)
        dz = np.sqrt(tmp_z / l)

    print("dx:", dx)
    print("dy:", dy)
    print("dz:", dz)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="rosbag file")
    parser.add_argument("-m", "--mode", help="mode (1:SD)")
    args = parser.parse_args()
    file_name = args.file_name
    mode = args.mode
    calculate_error(file_name, mode)
