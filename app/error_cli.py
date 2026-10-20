#!/usr/bin/env python3
"""設定JSONから実験ごとの位置・姿勢誤差時系列を保存するCLI。

使い方（リポジトリのトップから）::

    python3 app/error_cli.py parameters/example.json

入力は当面 ``inputs[0]`` の Pose bag に限定する。出力は ``time``,
``error_r``, ``error_theta`` を持つ npz で、付随情報は既存の ``__meta__``
形式で保存する。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from core import Dataset
from core.loaders import npz
from core.loaders import bag
from core.processing import error as error_processing
from core.processing import transform as transform_processing


DEFAULT_PID_TOPIC = "/gimbalrotor/debug/pose/pid"
PID_FIELDS = ("roll.err_p", "pitch.err_p", "yaw.err_p")


def _parser():
    parser = argparse.ArgumentParser(
        description="設定JSONから位置・姿勢誤差の時系列NPZを出力します。"
    )
    parser.add_argument("config", type=Path, help="実験設定JSON")
    parser.add_argument("--output", type=Path, help="出力NPZ（JSONの指定を上書き）")
    parser.add_argument(
        "--debug", action="store_true", help="エラー時にトレースバックを表示する"
    )
    return parser


def _path(value, base):
    path = Path(value).expanduser()
    return path if path.is_absolute() else base / path


def _read_config(config_path):
    with config_path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("設定JSONのトップレベルはオブジェクトにしてください")
    return config


def _target_position(experiment):
    target = experiment.get("target_position")
    if not isinstance(target, dict):
        raise ValueError("experiment.target_position が必要です")
    try:
        return np.array([float(target[key]) for key in ("x", "y", "z")])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "experiment.target_position には x, y, z の数値が必要です"
        ) from exc


def _transform_position(points, target, transform_spec):
    """plot_cli と同じ座標変換を現在位置と目標位置に適用する。"""
    if transform_spec is None:
        return points, target
    if not isinstance(transform_spec, dict):
        raise ValueError("inputs[0].transform はオブジェクトにしてください")

    channels = transform_spec.get("channels", ["x", "y", "z"])
    if channels != ["x", "y", "z"]:
        raise ValueError("誤差CLIの transform.channels は ['x', 'y', 'z'] にしてください")
    origin_spec = transform_spec.get("origin")
    if origin_spec is None or origin_spec == "none":
        origin = np.zeros(3)
    elif origin_spec == "target":
        origin = target.copy()
    elif isinstance(origin_spec, list) and len(origin_spec) == 3:
        try:
            origin = np.array([float(value) for value in origin_spec])
        except (TypeError, ValueError) as exc:
            raise ValueError("transform.origin は数値3要素が必要です") from exc
    else:
        raise ValueError("transform.origin は target / none / 3要素配列です")

    axis = transform_spec.get("axis")
    if axis not in (None, "x", "y", "z"):
        raise ValueError("transform.axis は null / x / y / z のいずれかです")
    try:
        angle = float(transform_spec.get("angle", 0.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("transform.angle は数値が必要です") from exc

    rotation = transform_processing.rotation_matrix(axis, angle)
    return (points - origin) @ rotation.T, (target - origin) @ rotation.T


def _pid_theta(pid_dataset):
    """PID の roll/pitch/yaw の err_p から record_pid.py と同じ θ を求める。"""
    rpy = np.stack([pid_dataset[field] for field in PID_FIELDS], axis=1)
    theta = np.full(len(pid_dataset), np.nan)
    valid = np.isfinite(rpy).all(axis=1)
    if valid.any():
        quaternion_w = Rotation.from_euler("xyz", rpy[valid]).as_quat()[:, 3]
        # record_pid.py の 2 * arccos(q.w) に合わせる。丸め誤差だけを補正する。
        theta[valid] = 2.0 * np.arccos(np.clip(quaternion_w, -1.0, 1.0))
    return theta


def _theta_on_pose_time(pose_dataset, pid_dataset):
    """PID の θ を、Pose の時刻軸へ補間する。時刻は bag 内の絶対時刻で合わせる。"""
    pid_theta = _pid_theta(pid_dataset)
    pid_time = pid_dataset.time + float(pid_dataset.meta.get("start_time", 0.0))
    pose_time = pose_dataset.time + float(pose_dataset.meta.get("start_time", 0.0))
    valid = np.isfinite(pid_theta) & np.isfinite(pid_time)
    if not valid.any():
        raise ValueError(f"PID トピック '{pid_dataset.meta.get('topic', '')}' に有効な err_p がありません")
    pid_time = pid_time[valid]
    pid_theta = pid_theta[valid]
    order = np.argsort(pid_time)
    pid_time = pid_time[order]
    pid_theta = pid_theta[order]
    pid_time, unique = np.unique(pid_time, return_index=True)
    pid_theta = pid_theta[unique]
    return np.interp(pose_time, pid_time, pid_theta, left=np.nan, right=np.nan)


def _output_path(config, config_path, override):
    if override is not None:
        return override if override.is_absolute() else config_path.parent / override
    setting = config.get("error_statistics", config.get("errors"))
    if isinstance(setting, str):
        setting = {"path": setting}
    if setting is not None and (not isinstance(setting, dict) or not setting.get("path")):
        raise ValueError("error_statistics.path（または errors.path）が必要です")
    if setting is not None:
        value = setting["path"]
    else:
        output = config.get("output")
        if isinstance(output, str):
            output_path = _path(output, config_path.parent)
        elif isinstance(output, dict) and output.get("path"):
            output_path = _path(output["path"], config_path.parent)
        else:
            output_path = None

        if output_path is not None and "_trajectory_" in output_path.stem:
            stem = output_path.stem.replace("_trajectory_", "_errors_", 1)
            filename = f"{stem}.npz"
        elif output_path is not None and output_path.stem.endswith("_trajectory"):
            filename = output_path.stem[:-len("_trajectory")] + "_errors.npz"
        elif output_path is not None:
            filename = f"{output_path.stem}_errors.npz"
        else:
            filename = f"{config_path.stem}_errors.npz"
        value = f"../stats/errors/{filename}"
    return _path(value, config_path.parent)


def generate(config, config_path, output_override=None):
    inputs = config.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise ValueError("inputs にPose bagを1つ以上指定してください")
    spec = inputs[0]
    if not isinstance(spec, dict):
        raise ValueError("inputs[0] はオブジェクトにしてください")
    if spec.get("type", "bag") != "bag" or spec.get("mode", "pose") != "pose":
        raise ValueError("誤差CLIの対象は inputs[0] の Pose bag です")
    if not spec.get("path") or not spec.get("topic"):
        raise ValueError("inputs[0] の bag path と topic が必要です")

    source_path = _path(spec["path"], config_path.parent)
    dataset = bag.load_pose(
        source_path,
        spec["topic"],
        time_source=spec.get("time_source", "receive"),
        name=spec.get("name"),
    )
    pid_topic = spec.get("pid_topic", DEFAULT_PID_TOPIC)
    if not isinstance(pid_topic, str) or not pid_topic:
        raise ValueError("inputs[0].pid_topic は空でない文字列が必要です")
    pid_dataset = bag.load(
        source_path,
        pid_topic,
        PID_FIELDS,
        time_source=spec.get("time_source", "receive"),
        name=f"{dataset.name}:{pid_topic}",
    )
    experiment = config.get("experiment", {})
    if not isinstance(experiment, dict):
        raise ValueError("experiment はオブジェクトにしてください")

    original_target = _target_position(experiment)
    target = original_target.copy()
    points = np.stack([dataset[key] for key in ("x", "y", "z")], axis=1)
    points, target = _transform_position(points, target, spec.get("transform"))
    position_dataset = Dataset(
        name=dataset.name,
        time=dataset.time,
        channels={"x": points[:, 0], "y": points[:, 1], "z": points[:, 2]},
        units={"x": "m", "y": "m", "z": "m"},
    )
    error_r = error_processing.position_error(
        position_dataset, ("x", "y", "z"), targets=target, name="error_r"
    )["error_r"] * 1000.0

    error_theta = _theta_on_pose_time(dataset, pid_dataset)

    start = experiment.get("task_start")
    end = experiment.get("task_end")
    mask = np.ones(len(dataset), dtype=bool)
    if start is not None:
        mask &= dataset.time >= float(start)
    if end is not None:
        mask &= dataset.time <= float(end)
    if not mask.any():
        raise ValueError(f"task_start/task_end の範囲にデータがありません: [{start}, {end}]")
    time = dataset.time[mask]
    time = time - time[0]

    experiment_name = config_path.stem
    metadata = {
        "experiment": experiment_name,
        "target_position": original_target.tolist(),
        "start": start,
        "end": end,
        "source": str(source_path),
        "topic": spec["topic"],
        "pid_topic": pid_topic,
    }
    result = Dataset(
        name=experiment_name,
        time=time,
        channels={"error_r": error_r[mask], "error_theta": error_theta[mask]},
        units={"error_r": "mm", "error_theta": "rad"},
        meta=metadata,
    )
    output_path = _output_path(config, config_path, output_override)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    npz.save(result, output_path)
    return output_path


def main(argv=None):
    args = _parser().parse_args(argv)
    config_path = args.config.expanduser().resolve()
    try:
        output_path = generate(_read_config(config_path), config_path, args.output)
    except Exception as exc:
        print(f"error-cli: エラー: {exc}", file=sys.stderr)
        if args.debug:
            raise
        return 1
    print(f"errors: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
