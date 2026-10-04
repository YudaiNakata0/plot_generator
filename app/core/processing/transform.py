"""位置の座標変換（平行移動 + 軸まわりの回転）。

傾いた壁面に沿った座標系で軌跡を見るためのもの（scripts/draw_trajectory.py の -a/-p）。
    p' = R_axis(angle) · (p - origin)
元のスクリプトの 2D（x 軸法線）は origin = 目標位置, axis = "y", angle = pitch に相当する。
変換したチャンネルは名前に接尾辞（既定は "'"）を付けて Dataset に追加し、元のチャンネルは残す。
"""
from __future__ import annotations

import numpy as np

AXES = ("x", "y", "z")


def rotation_matrix(axis, angle):
    """軸まわりの回転行列（右手系、angle [rad] が正なら軸の正の向きから見て反時計回り）。

    R_y は scripts/draw_trajectory.py の R_y と同じ。axis が None なら単位行列。
    """
    if axis is None or angle == 0:
        return np.eye(3)
    c, s = np.cos(angle), np.sin(angle)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    if axis == "z":
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    raise ValueError(f"invalid axis: {axis} (expected one of {AXES} or None)")


def target_origin(dataset, channels):
    """3 チャンネルの目標値 (meta["target"]) を原点として返す。1 つでも無ければ None。"""
    origin = [dataset.target_for(ch) for ch in channels]
    return None if any(v is None for v in origin) else tuple(origin)


def transform_position(dataset, channels=AXES, origin=None, axis=None, angle=0.0, suffix="'"):
    """3 チャンネル (x, y, z) を変換し、接尾辞付きのチャンネルとして追加した Dataset を返す。

    origin: 原点 (3 要素) か None（平行移動しない）
    axis / angle: 回転軸 ("x"/"y"/"z"/None) と角度 [rad]
    目標値が 3 チャンネルともあれば、同じ変換をかけた値を新しいチャンネルの目標値にする
    （origin = 目標位置なら 0 になる）。
    """
    channels = tuple(channels)
    if len(channels) != 3:
        raise ValueError(f"3 チャンネル必要です: {channels}")
    if not suffix:
        raise ValueError("接尾辞が空だと元のチャンネルを上書きしてしまいます")
    missing = [ch for ch in channels if ch not in dataset]
    if missing:
        raise KeyError(f"{dataset.name}: no channel {missing}")

    offset = np.zeros(3) if origin is None else np.asarray(origin, dtype=float)
    rotation = rotation_matrix(axis, angle)
    points = np.stack([dataset[ch] for ch in channels], axis=1) - offset
    transformed = points @ rotation.T

    result = dataset
    names = [ch + suffix for ch in channels]
    for i, (ch, name) in enumerate(zip(channels, names)):
        result = result.with_channel(name, transformed[:, i], dataset.unit(ch))

    meta = dict(result.meta)
    targets = dict(meta.get("target", {}))
    original_target = target_origin(dataset, channels)
    if original_target is not None:
        new_target = rotation @ (np.asarray(original_target) - offset)
        for name, value in zip(names, new_target):
            # 浮動小数の誤差で -0.0 や 1e-17 にならないように丸める
            targets["t" + name] = float(np.round(value, 12)) + 0.0
    else:
        for name in names:
            targets.pop("t" + name, None)
    if targets:
        meta["target"] = targets

    history = list(meta.get("transforms", []))
    history.append({
        "channels": list(channels),
        "outputs": names,
        "origin": None if origin is None else [float(v) for v in offset],
        "axis": axis,
        "angle": float(angle),
    })
    meta["transforms"] = history
    return result.__class__(result.name, result.time, result.channels, result.units, meta)
