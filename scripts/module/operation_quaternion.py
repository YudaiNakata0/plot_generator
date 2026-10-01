#!/usr/bin/env python3
import numpy as np
from scipy.spatial.transform import Rotation
from geometry_msgs.msg import Pose, Quaternion

# オイラー角からクォータニオンへの変換
def euler_to_quaternion(euler_angles):
    rotation = Rotation.from_euler("xyz", euler_angles)
    quaternion = rotation.as_quat()
    msg = Quaternion()
    msg.x = quaternion[0]
    msg.y = quaternion[1]
    msg.z = quaternion[2]
    msg.w = quaternion[3]
    return msg

# クォータニオンからオイラー角への変換
def quaternion_to_euler(quaternion):
    rotation = Rotation.from_quat(np.array([quaternion.x,
                                            quaternion.y,
                                            quaternion.z,
                                            quaternion.w]))
    euler_angles = rotation.as_euler("xyz")
    return euler_angles

# Pose型メッセージの生成　入力：7要素配列　出力：Pose型
def makepose_fromarray(array):
    pose = Pose()
    pose.position.x = array[0]
    pose.position.y = array[1]
    pose.position.z = array[2]
    pose.orientation.x = array[3]
    pose.orientation.y = array[4]
    pose.orientation.z = array[5]
    pose.orientation.w = array[6]
    return pose

# 回転インスタンスの生成　入力：Quaternion型　出力：Rotationインスタンス
def makeinstance_rotation(quat):
    rot = Rotation.from_quat(np.array([quat.x, quat.y, quat.z, quat.w]))
    return rot

# クオータニオンの合成　入力：Quaternion型(2)　出力：Quaternion型
def synthesize_quaternion(quat1, quat2):
    new_quat = Quaternion()
    rot1 = makeinstance_rotation(quat1)
    rot2 = makeinstance_rotation(quat2)
    new_rot = rot1*rot2
    new_quat.x = new_rot.as_quat()[0]
    new_quat.y = new_rot.as_quat()[1]
    new_quat.z = new_rot.as_quat()[2]
    new_quat.w = new_rot.as_quat()[3]
    return new_quat
    
# 位置、姿勢の合成　入力：Pose型(2)　出力：Pose型
def add_pose(pose1, pose2):
    new_pose = Pose()
    new_pose.position.x = pose1.position.x + pose2.position.x
    new_pose.position.y = pose1.position.y + pose2.position.y
    new_pose.position.z = pose1.position.z + pose2.position.z
    new_pose.orientation = synthesize_quaternion(pose1.orientation, pose2.orientation)
    return new_pose

# 共役クオータニオンの生成　入力：Quaternion型　出力：Quaternion型
def conjugate(quat):
    conj_quat = Quaternion()
    conj_quat.x = -quat.x
    conj_quat.y = -quat.y
    conj_quat.z = -quat.z
    conj_quat.w = quat.w
    return conj_quat

# 始状態から終状態へのクオータニオンの逆計算　入力：Quaternion型(2)　出力：Quaternion型
def inverse_calculate_quaternion(quat_start, quat_end):
    move_quat = synthesize_quaternion(conjugate(quat_start), quat_end)
    return move_quat

# 位置、姿勢の差分　入力：Pose型(2)　出力：Pose型
def difference_pose(pose_ref, pose):
    adj_pose = Pose()
    adj_pose.position.x = pose.position.x - pose_ref.position.x
    adj_pose.position.y = pose.position.y - pose_ref.position.y
    adj_pose.position.z = pose.position.z - pose_ref.position.z
    adj_pose.orientation = inverse_calculate_quaternion(pose_ref.orientation, pose.orientation)
    return adj_pose
