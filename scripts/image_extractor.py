#!/usr/bin/env python3
import rosbag
import rospy
import cv2
import os
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
import argparse

def image_extractor(file_name, topic_name, output_directory, start_time, end_time, duration):
    # ========================
    # 設定
    # ========================
    file_path = os.path.normpath(os.path.join(os.getcwd(), file_name))
    output_dir = os.path.normpath(os.path.join(os.getcwd(), output_directory))

    # ========================
    # 初期化
    # ========================
    os.makedirs(output_directory, exist_ok=True)
    bridge = CvBridge()

    bag = rosbag.Bag(file_path)

    bag_start_time = bag.get_start_time()
    start_time = rospy.Time.from_sec(bag_start_time + start_time)
    end_time = rospy.Time.from_sec(bag_start_time + end_time)

    next_save_time = start_time
    saved_count = 0

    # ========================
    # rosbag 読み込み
    # ========================
    for topic, msg, t in bag.read_messages(topics=[topic_name]):
        if t > end_time:
            break

        if t < start_time:
            continue

        if t >= next_save_time:
            try:
                cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            except Exception as e:
                print("cv_bridge error:", e)
                continue

            timestamp = int(t.to_sec() - bag_start_time)
            filename = os.path.join(
                output_directory,
                f"image_{saved_count:04d}_{timestamp}.png"
            )
            cv2.imwrite(filename, cv_image)

            print(f"Saved: {filename}")

            saved_count += 1
            next_save_time += rospy.Duration(duration)

    bag.close()
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", help="rosbag file")
    parser.add_argument("--topic_name", default="/usb_cam/image_raw", help="topic name(Pose type)")
    parser.add_argument("-o", "--output_directory", default="bag_extracted_images/", help="output directory")
    parser.add_argument("-s", "--start_time", default="0", help="start time")
    parser.add_argument("-e", "--end_time", default="1000", help="end time")
    parser.add_argument("-d", "--duration", default="1", help="capture duration")
    args = parser.parse_args()
    file_name = args.file_name
    topic_name = args.topic_name
    output_directory = args.output_directory
    s = float(args.start_time)
    e = float(args.end_time)
    d = float(args.duration)
    image_extractor(file_name, topic_name, output_directory, s, e, d)
