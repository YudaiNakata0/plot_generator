"""rosbag (.bag) から Dataset を作る。

フィールドは "pose.position.x" / "acc[0]" / "poses[0].pose.position.x" のような
パス文字列で指定する。メッセージ型は bag に埋め込まれた定義から復元されるので、
独自メッセージ型 (spinal/* など) もパッケージ無しで読める。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

import numpy as np
import rosbag

from ..dataset import Dataset

NUMERIC_TYPES = {
    "bool", "byte", "char",
    "int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64",
    "float32", "float64",
}
TIME_TYPES = {"time", "duration"}

# 配列フィールドはこの長さまで要素ごとに展開する（画像の data などは対象外にする）
MAX_ARRAY_LENGTH = 32

# 進捗コールバックを呼ぶ間隔 [message]
PROGRESS_INTERVAL = 1000


@dataclass(frozen=True)
class TopicInfo:
    name: str
    msg_type: str
    message_count: int
    frequency: float | None


@dataclass(frozen=True)
class FieldInfo:
    path: str
    type: str


def list_topics(bag_path) -> dict[str, TopicInfo]:
    """bag に含まれるトピックの一覧を返す。"""
    with rosbag.Bag(bag_path) as bag:
        info = bag.get_type_and_topic_info()
    return {
        topic: TopicInfo(topic, val.msg_type, val.message_count, val.frequency)
        for topic, val in sorted(info.topics.items())
    }


def list_fields(bag_path, topic) -> list[FieldInfo]:
    """トピックの最初のメッセージをたどり、数値として読めるフィールドの一覧を返す。"""
    with rosbag.Bag(bag_path) as bag:
        for _, msg, _ in bag.read_messages(topics=[topic]):
            return list(_walk_message(msg, ""))
    return []


def _split_type(slot_type):
    """'float32[3]' -> ('float32', True), 'geometry_msgs/Pose' -> ('geometry_msgs/Pose', False)"""
    if slot_type.endswith("]"):
        return slot_type[:slot_type.index("[")], True
    return slot_type, False


def _walk_message(msg, prefix):
    for slot, slot_type in zip(msg.__slots__, msg._slot_types):
        value = getattr(msg, slot)
        path = f"{prefix}.{slot}" if prefix else slot
        base, is_array = _split_type(slot_type)
        if is_array:
            if len(value) > MAX_ARRAY_LENGTH:
                continue
            for i, item in enumerate(value):
                yield from _walk_value(item, base, f"{path}[{i}]")
        else:
            yield from _walk_value(value, base, path)


def _walk_value(value, base, path):
    if base in NUMERIC_TYPES or base in TIME_TYPES:
        yield FieldInfo(path, base)
    elif hasattr(value, "__slots__"):
        # nest
        yield from _walk_message(value, path)
    # string などは数値にできないので除外


_TOKEN = re.compile(r"^(\w+)((?:\[\d+\])*)$")


def _compile_path(path):
    """'poses[0].pose.position.x' -> [('poses', [0]), ('pose', []), ('position', []), ('x', [])]"""
    steps = []
    for token in path.split("."):
        m = _TOKEN.match(token)
        if m is None:
            raise ValueError(f"invalid field path: {path}")
        indices = [int(i) for i in re.findall(r"\[(\d+)\]", m.group(2))]
        steps.append((m.group(1), indices))
    return steps


def _get_value(msg, steps):
    value = msg
    for attr, indices in steps:
        value = getattr(value, attr)
        for i in indices:
            value = value[i]
    if hasattr(value, "to_sec"):
        # time / duration
        return value.to_sec()
    return float(value)


def get_field(msg, path):
    """メッセージからパス文字列で指定したフィールドの値を float で取り出す。"""
    return _get_value(msg, _compile_path(path))


def load(bag_path, topic, fields, time_source="receive", name=None, progress=None) -> Dataset:
    """bag の 1 トピックから指定フィールドを読み込む。

    time_source:
        "receive" : bag に記録された受信時刻（scripts/ と同じ）
        "header"  : メッセージの header.stamp
    progress: progress(読んだ数, 全体の数) を定期的に呼ぶコールバック
    存在しない配列要素などで取り出せない値は NaN になる。
    """
    if time_source not in ("receive", "header"):
        raise ValueError(f"invalid time_source: {time_source}")
    fields = list(fields)
    compiled = [_compile_path(path) for path in fields]

    with rosbag.Bag(bag_path) as bag:
        info = bag.get_type_and_topic_info().topics
        if topic not in info:
            raise KeyError(f"{bag_path}: no topic '{topic}'")
        total = info[topic].message_count
        msg_type = info[topic].msg_type

        time = np.empty(total)
        values = np.full((len(fields), total), np.nan)
        count = 0
        for _, msg, t in bag.read_messages(topics=[topic]):
            if time_source == "header":
                if not hasattr(msg, "header"):
                    raise ValueError(f"{topic} ({msg_type}) has no header")
                time[count] = msg.header.stamp.to_sec()
            else:
                time[count] = t.to_sec()
            for i, steps in enumerate(compiled):
                try:
                    values[i, count] = _get_value(msg, steps)
                except (IndexError, AttributeError, TypeError, ValueError):
                    pass
            count += 1
            if progress and count % PROGRESS_INTERVAL == 0:
                progress(count, total)

    if count == 0:
        raise ValueError(f"{bag_path}: topic '{topic}' has no message")
    time = time[:count]
    values = values[:, :count]
    if progress:
        progress(count, total)

    # adjust time(start from 0)
    start_time = time[0]
    time = time - start_time

    if name is None:
        name = f"{os.path.splitext(os.path.basename(bag_path))[0]}:{topic}"
    return Dataset(
        name=name,
        time=time,
        channels={path: values[i] for i, path in enumerate(fields)},
        meta={
            "source": os.path.abspath(bag_path),
            "topic": topic,
            "msg_type": msg_type,
            "time_source": time_source,
            "start_time": start_time,
        },
    )


# ===== よく使うメッセージ型 =====

# メッセージ型 -> Pose 部分へのパス
_POSE_PREFIX = {
    "geometry_msgs/Pose": "",
    "geometry_msgs/PoseStamped": "pose.",
    "geometry_msgs/PoseWithCovarianceStamped": "pose.pose.",
    "nav_msgs/Odometry": "pose.pose.",
}
_POSE_FIELDS = {
    "x": "position.x", "y": "position.y", "z": "position.z",
    "qx": "orientation.x", "qy": "orientation.y", "qz": "orientation.z", "qw": "orientation.w",
}

# メッセージ型 -> Wrench 部分へのパス
_WRENCH_PREFIX = {
    "geometry_msgs/Wrench": "",
    "geometry_msgs/WrenchStamped": "wrench.",
}
_WRENCH_FIELDS = {
    "force_x": "force.x", "force_y": "force.y", "force_z": "force.z",
    "torque_x": "torque.x", "torque_y": "torque.y", "torque_z": "torque.z",
}


POSE_TYPES = tuple(_POSE_PREFIX)
WRENCH_TYPES = tuple(_WRENCH_PREFIX)


def _topic_type(bag_path, topic):
    topics = list_topics(bag_path)
    if topic not in topics:
        raise KeyError(f"{bag_path}: no topic '{topic}'")
    return topics[topic].msg_type


def _load_known(bag_path, topic, prefixes, fields, units, **kwargs):
    msg_type = _topic_type(bag_path, topic)
    if msg_type not in prefixes:
        raise TypeError(f"{topic} is {msg_type}, expected one of {list(prefixes)}")
    prefix = prefixes[msg_type]
    mapping = {prefix + path: key for key, path in fields.items()}
    ds = load(bag_path, topic, mapping.keys(), **kwargs).rename(mapping)
    return Dataset(ds.name, ds.time, ds.channels, units, ds.meta)


def load_pose(bag_path, topic, **kwargs) -> Dataset:
    """Pose 系トピックを x, y, z [m], qx, qy, qz, qw のチャンネル名で読み込む。"""
    units = {"x": "m", "y": "m", "z": "m"}
    return _load_known(bag_path, topic, _POSE_PREFIX, _POSE_FIELDS, units, **kwargs)


def load_wrench(bag_path, topic, **kwargs) -> Dataset:
    """Wrench 系トピックを force_x/y/z [N], torque_x/y/z [N·m] のチャンネル名で読み込む。"""
    units = {key: ("N" if key.startswith("force") else "N·m") for key in _WRENCH_FIELDS}
    return _load_known(bag_path, topic, _WRENCH_PREFIX, _WRENCH_FIELDS, units, **kwargs)
