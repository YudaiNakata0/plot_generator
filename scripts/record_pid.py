import rosbag
import numpy as np
import matplotlib.pyplot as plt
from aerial_robot_msgs.msg import PoseControlPid
import argparse
import os
from module import operation_quaternion as oq

TOPIC_NAME = '/gimbalrotor/debug/pose/pid'  # Define the topic name as a constant

def record_pid(file_name, start_time=None, end_time=None):
    # path conversion
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    # open bag file
    bag = rosbag.Bag(file_path)

    # initialize
    time = []
    theta = []

    # read data
    for topic, msg, t in bag.read_messages(topics=[TOPIC_NAME]):
        time.append(t.to_sec())
        dr = msg.roll.err_p
        dp = msg.pitch.err_p
        dy = msg.yaw.err_p
        q = oq.euler_to_quaternion([dr, dp, dy])
        theta_err = np.arccos(q.w) * 2.0
        theta.append(theta_err)

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

    fig, ax = plt.subplots()
    ax.plot(time, theta, label='Theta Error', color='blue')
    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Theta Error [rad]')
    ax.set_title('Theta Error over Time')
    ax.grid()
    ax.legend()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="rosbag file")
    parser.add_argument("-s", "--start_time",  help="start time")
    parser.add_argument("-e", "--end_time", help="end time")
    args = parser.parse_args()
    file_name = args.file_name
    s = args.start_time
    e = args.end_time
    record_pid(file_name, s, e)