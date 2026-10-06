"""目標値との誤差（派生チャンネル）の計算。

    axis_errors       : 各軸の誤差 v - 目標値（scripts/calculate_error.py -s の誤差）
    position_error    : 位置誤差 r = sqrt(Σ (v - 目標値)^2)（scripts/calculate_error_rad.py）
    orientation_error : 姿勢誤差 θ。roll, pitch, yaw をクォータニオンにして目標姿勢との差の回転角を求める
                        （scripts/record_orientation.py）

結果は新しいチャンネルとして Dataset に追加し、元のチャンネルは残す。
誤差のチャンネルには目標値 0 を設定するので、統計の RMSE がそのまま RMS 誤差になる。
"""
from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation

AXIS_SUFFIX = "_err"
# Rotation.from_euler の規約（scripts/module/operation_quaternion.py と同じ。小文字 = 固定軸まわり）
EULER_ORDER = "xyz"


def resolve_targets(dataset, channels, targets=None):
    """チャンネルごとの目標値のタプルを返す。

    targets は channels と同じ長さの値のリスト（None の要素は Dataset の meta["target"] で補う）。
    見つからないチャンネルがあれば ValueError。
    """
    channels = tuple(channels)
    given = [None] * len(channels) if targets is None else list(targets)
    if len(given) != len(channels):
        raise ValueError(f"目標値の数がチャンネルの数と合いません: {len(given)} / {len(channels)}")
    result = [dataset.target_for(ch) if value is None else value
              for ch, value in zip(channels, given)]
    missing = [ch for ch, value in zip(channels, result) if value is None]
    if missing:
        raise ValueError(f"{dataset.name}: 目標値がありません: {', '.join(missing)}")
    return tuple(float(v) for v in result)


def _check_channels(dataset, channels, count=None):
    channels = tuple(channels)
    if count is not None and len(channels) != count:
        raise ValueError(f"{count} チャンネル必要です: {channels}")
    if len(set(channels)) != len(channels):
        raise ValueError(f"同じチャンネルが重複しています: {channels}")
    missing = [ch for ch in channels if ch not in dataset]
    if missing:
        raise KeyError(f"{dataset.name}: no channel {missing}")
    return channels


def _add_result(dataset, outputs, kind, channels, targets):
    """outputs {名前: (値, 単位)} を追加し、目標値 0 と履歴を meta に入れた Dataset を返す。"""
    result = dataset
    for name, (values, unit) in outputs.items():
        result = result.with_channel(name, values, unit)
    meta = dict(result.meta)
    meta_targets = dict(meta.get("target", {}))
    for name in outputs:
        meta_targets["t" + name] = 0.0
    meta["target"] = meta_targets
    history = list(meta.get("errors", []))
    history.append({
        "kind": kind,
        "channels": list(channels),
        "targets": [float(v) for v in targets],
        "outputs": list(outputs),
    })
    meta["errors"] = history
    return result.__class__(result.name, result.time, result.channels, result.units, meta)


def axis_errors(dataset, channels, targets=None, suffix=AXIS_SUFFIX):
    """各チャンネルの誤差 v - 目標値 を、名前 + 接尾辞のチャンネルとして追加した Dataset を返す。"""
    channels = _check_channels(dataset, channels)
    if not suffix:
        raise ValueError("接尾辞が空だと元のチャンネルを上書きしてしまいます")
    targets = resolve_targets(dataset, channels, targets)
    outputs = {ch + suffix: (dataset[ch] - target, dataset.unit(ch))
               for ch, target in zip(channels, targets)}
    return _add_result(dataset, outputs, "axis", channels, targets)


def position_error(dataset, channels, targets=None, name="r"):
    """位置誤差 r = 目標位置とのユークリッド距離 を、チャンネル name として追加した Dataset を返す。"""
    channels = _check_channels(dataset, channels)
    if name in channels:
        raise ValueError("出力チャンネル名が入力チャンネルと同じです")
    targets = resolve_targets(dataset, channels, targets)
    diff = np.stack([dataset[ch] - target for ch, target in zip(channels, targets)], axis=1)
    r = np.sqrt(np.sum(diff ** 2, axis=1))
    return _add_result(dataset, {name: (r, dataset.unit(channels[0]))}, "position", channels, targets)


def orientation_angle(rpy, target_rpy):
    """roll, pitch, yaw (N, 3) [rad] と目標 (3,) から、目標との差の回転角 θ (N,) [rad] を返す。

    dq = conj(q) * q_target の回転角（2·arccos(|dq.w|), 0〜π）。q と -q は同じ姿勢なので |w| を使う。
    NaN を含む行は NaN にする。
    """
    rpy = np.asarray(rpy, dtype=float)
    theta = np.full(len(rpy), np.nan)
    valid = ~np.isnan(rpy).any(axis=1)
    if valid.any():
        q = Rotation.from_euler(EULER_ORDER, rpy[valid])
        q_target = Rotation.from_euler(EULER_ORDER, np.asarray(target_rpy, dtype=float))
        theta[valid] = (q.inv() * q_target).magnitude()
    return theta


def orientation_error(dataset, channels=("roll", "pitch", "yaw"), targets=None, name="theta"):
    """姿勢誤差 θ [rad] を、チャンネル name として追加した Dataset を返す。"""
    channels = _check_channels(dataset, channels, count=3)
    if name in channels:
        raise ValueError("出力チャンネル名が入力チャンネルと同じです")
    targets = resolve_targets(dataset, channels, targets)
    rpy = np.stack([dataset[ch] for ch in channels], axis=1)
    theta = orientation_angle(rpy, targets)
    return _add_result(dataset, {name: (theta, "rad")}, "orientation", channels, targets)
