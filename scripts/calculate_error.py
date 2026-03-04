#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from geometry_msgs.msg import Pose, PoseStamped
import argparse
import os

def calculate_error(file_name, mode=None, x=None, y=None, z=None, tx=None, ty=None, tz=None, s=None):
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    if mode:
        mode = int(mode)
    # data name
    if x:
        name_x = x
    if y:
        name_y = y
    if z:
        name_z = z
    if tx:
        name_tx = tx
    if ty:
        name_ty = ty
    if tz:
        name_tz = tz

    # read data from npz file
    data = np.load(file_path)
    time = data["time"]
    x = data[name_x]
    y = data[name_y]
    z = data[name_z]
    l = np.array([len(x), len(y), len(z)]).min()
    tx = data[name_tx]
    ty = data[name_ty]
    tz = data[name_tz]

    # record
    error_x = []
    error_y = []
    error_z = []

    if mode == 1:
        dx = np.std(x)
        dy = np.std(y)
        dz = np.std(z)
        mx = np.mean(x)
        my = np.mean(y)
        mz = np.mean(z)
        print("Mean: ", mx, ",", my, ",", mz)

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
        # save file
        if s:
            for i in range(l):
                ex = x[i] - tx
                ey = y[i] - ty
                ez = z[i] - tz
                error_x.append(ex)
                error_y.append(ey)
                error_z.append(ez)
            name = file_name[:-4] + "_rpy" + ".npz"
            np.savez(name, time=time[:l], roll=error_x, pitch=error_y, yaw=error_z)

    print("dx:", dx)
    print("dy:", dy)
    print("dz:", dz)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="rosbag file")
    parser.add_argument("-m", "--mode", help="mode (1:SD)")
    parser.add_argument("-x", "--data_x", help="data name for x")
    parser.add_argument("-y", "--data_y", help="data name for y")
    parser.add_argument("-z", "--data_z", help="data name for z")
    parser.add_argument("--tx", help="data name for target x")
    parser.add_argument("--ty", help="data name for target y")
    parser.add_argument("--tz", help="data name for target z")
    parser.add_argument("-s", "--save", help="save data as npz file")
    args = parser.parse_args()
    file_name = args.file_name
    mode = args.mode
    x = args.data_x
    y = args.data_y
    z = args.data_z
    tx = args.tx
    ty = args.ty
    tz = args.tz
    s = args.save
    calculate_error(file_name, mode, x, y, z, tx, ty, tz, s)
