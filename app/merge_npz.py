#!/usr/bin/env python3
"""複数の時系列 NPZ を 1 つの NPZ にまとめる CLI。

例::

    python3 app/merge_npz.py stats/errors/*_errors_*.npz \
        --output stats/errors/all_errors.npz

入力ファイルは同じキー構成である必要があり、各 1 次元配列を入力順に
連結する。``time`` は既定で各ファイルの先頭を 0 にそろえたあと、連結後
も単調増加するように時間をずらす。統計や箱ひげ図用に時刻を使わない場合
でも、各入力のサンプル数は他の配列と一致している必要がある。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


META_KEY = "__meta__"


def _read_metadata(value):
    """NPZ の __meta__ を読み、壊れている場合は空の情報として扱う。"""
    try:
        info = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return info if isinstance(info, dict) else {}


def _continuous_time(chunks):
    result = []
    offset = 0.0
    for index, values in enumerate(chunks):
        values = np.asarray(values, dtype=float).ravel()
        if values.size == 0:
            result.append(values)
            continue
        start = values[0]
        shifted = values - start + offset
        result.append(shifted)
        if index < len(chunks) - 1:
            duration = shifted[-1] - shifted[0]
            offset = shifted[-1] + max(float(duration), 0.0) / max(values.size - 1, 1)
    return np.concatenate(result) if result else np.array([], dtype=float)


def merge_npz_files(paths, output, time_mode="continuous"):
    paths = [Path(path).expanduser().resolve() for path in paths]
    output = Path(output).expanduser().resolve()
    if not paths:
        raise ValueError("入力 NPZ が指定されていません")

    unique_paths = []
    seen = set()
    for path in paths:
        if path == output:
            continue
        if path not in seen:
            unique_paths.append(path)
            seen.add(path)
    paths = unique_paths
    if not paths:
        raise ValueError("出力ファイル自身は入力にできません")

    loaded = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"入力ファイルがありません: {path}")
        with np.load(path, allow_pickle=False) as data:
            arrays = {key: np.asarray(data[key]) for key in data.files if key != META_KEY}
            metadata = _read_metadata(data[META_KEY]) if META_KEY in data else {}
        if not arrays:
            raise ValueError(f"データ配列がありません: {path}")
        loaded.append((path, arrays, metadata))

    keys = set(loaded[0][1])
    for path, arrays, _ in loaded[1:]:
        other_keys = set(arrays)
        if other_keys != keys:
            missing = sorted(keys - other_keys)
            extra = sorted(other_keys - keys)
            details = []
            if missing:
                details.append(f"不足: {', '.join(missing)}")
            if extra:
                details.append(f"余分: {', '.join(extra)}")
            raise ValueError(f"キー構成が一致しません ({path}; {'; '.join(details)})")

    lengths = []
    for path, arrays, _ in loaded:
        length = None
        for key, values in arrays.items():
            if values.ndim != 1:
                raise ValueError(f"'{key}' は 1 次元配列ではありません: {path}")
            if not np.issubdtype(values.dtype, np.number):
                raise ValueError(f"'{key}' は数値配列ではありません: {path}")
            if length is None:
                length = len(values)
            elif len(values) != length:
                raise ValueError(f"{path} の配列長が一致しません: '{key}'")
        lengths.append(length)

    merged = {}
    for key in loaded[0][1]:
        values = [arrays[key] for _, arrays, _ in loaded]
        if key == "time" and time_mode == "continuous":
            merged[key] = _continuous_time(values)
        else:
            merged[key] = np.concatenate(values)

    first_info = loaded[0][2]
    info = {
        "name": output.stem,
        "units": first_info.get("units", {}),
        "meta": dict(first_info.get("meta", {})),
    }
    info["meta"]["merged_files"] = [str(path) for path in paths]
    info["meta"]["time_mode"] = time_mode
    info["meta"].pop("source", None)
    merged[META_KEY] = np.array(json.dumps(info, ensure_ascii=False))

    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output, **merged)
    return output, sum(lengths)


def main(argv=None):
    parser = argparse.ArgumentParser(description="複数の時系列 NPZ を 1 つにまとめます")
    parser.add_argument("npz_files", nargs="+", type=Path, help="入力 NPZ（入力順に連結）")
    parser.add_argument("-o", "--output", required=True, type=Path, help="出力 NPZ")
    parser.add_argument(
        "--time-mode",
        choices=("continuous", "preserve"),
        default="continuous",
        help="time の扱い（既定: 連結後も単調増加。preserve は値をそのまま連結）",
    )
    args = parser.parse_args(argv)
    try:
        output, count = merge_npz_files(args.npz_files, args.output, args.time_mode)
    except (OSError, ValueError, KeyError) as exc:
        print(f"merge-npz: エラー: {exc}", file=sys.stderr)
        return 1
    print(f"saved: {output} ({count} samples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
