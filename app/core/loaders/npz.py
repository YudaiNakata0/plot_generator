"""npz ファイルと Dataset の相互変換。

scripts/ が出力した data/*.npz と互換:
    - "time" キーを時刻として使う（無ければ 0, 1, 2, ... の連番）
    - time と同じ長さの配列はチャンネル
    - 値が 1 つだけのもの (tx, troll など) は目標値として meta["target"] に入れる
保存時は単位などの付随情報を JSON 文字列にして "__meta__" キーに入れる。
目標値は scripts/ でも読めるように、これまで通りトップレベルのキーとして保存する。
"""
from __future__ import annotations

import json
import os

import numpy as np

from ..dataset import Dataset

META_KEY = "__meta__"

# キー名からの単位の推定
_GUESS_UNITS = {
    "x": "m", "y": "m", "z": "m", "r": "m",
    "roll": "rad", "pitch": "rad", "yaw": "rad", "theta": "rad",
}


def load(npz_path, name=None) -> Dataset:
    with np.load(npz_path) as data:
        arrays = {key: data[key] for key in data.files}

    info = {}
    if META_KEY in arrays:
        info = json.loads(str(arrays.pop(META_KEY)))

    if "time" in arrays:
        time = np.asarray(arrays.pop("time"), dtype=float).ravel()
    else:
        length = max((v.size for v in arrays.values() if v.ndim == 1), default=0)
        time = np.arange(length, dtype=float)

    channels = {}
    targets = {}
    skipped = []
    for key, values in arrays.items():
        if values.ndim == 1 and len(values) == len(time):
            channels[key] = values
        elif values.size == 1 and np.issubdtype(values.dtype, np.number):
            targets[key] = float(values)
        else:
            skipped.append(key)

    units = {key: unit for key, unit in _GUESS_UNITS.items() if key in channels}
    units.update(info.get("units", {}))

    meta = dict(info.get("meta", {}))
    meta["source"] = os.path.abspath(npz_path)
    if targets:
        meta["target"] = targets
    if skipped:
        meta["skipped_keys"] = skipped

    if name is None:
        name = info.get("name") or os.path.splitext(os.path.basename(npz_path))[0]
    return Dataset(name=name, time=time, channels=channels, units=units, meta=meta)


def save(dataset, npz_path):
    reserved = {"time", META_KEY}
    conflicts = reserved & set(dataset.channels)
    if conflicts:
        raise ValueError(f"channel name {sorted(conflicts)} is reserved")

    meta = {key: value for key, value in dataset.meta.items() if key != "target"}
    info = {"name": dataset.name, "units": dataset.units, "meta": meta}

    arrays = dict(dataset.channels)
    for key, value in dataset.targets.items():
        if key in arrays or key in reserved:
            raise ValueError(f"target key '{key}' conflicts with a channel name")
        arrays[key] = value
    arrays["time"] = dataset.time
    arrays[META_KEY] = np.array(json.dumps(info, ensure_ascii=False, default=_to_json))
    np.savez(npz_path, **arrays)


def _to_json(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"{type(value).__name__} is not JSON serializable")
