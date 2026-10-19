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

from core import Dataset
from core.loaders import npz
from core.loaders import bag
from core.processing import error as error_processing
from core.processing import transform as transform_processing


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


def _output_path(config, config_path, override):
    if override is not None:
        return override if override.is_absolute() else config_path.parent / override
    setting = config.get("error_statistics", config.get("errors"))
    if isinstance(setting, str):
        setting = {"path": setting}
    if setting is not None and (not isinstance(setting, dict) or not setting.get("path")):
        raise ValueError("error_statistics.path（または errors.path）が必要です")
    value = setting["path"] if setting is not None else f"../stats/errors/{config_path.stem}_errors.npz"
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

    transform_spec = spec.get("transform") or {}
    try:
        angle = float(transform_spec.get("angle", 0.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("transform.angle は数値が必要です") from exc
    target_rpy = np.array([0.0, -angle, 0.0])
    quaternions = np.stack([dataset[key] for key in ("qx", "qy", "qz", "qw")], axis=1)
    error_theta = error_processing.orientation_angle_from_quaternion(
        quaternions, target_rpy
    )

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
        "target_rpy": target_rpy.tolist(),
        "start": start,
        "end": end,
        "source": str(source_path),
        "topic": spec["topic"],
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
