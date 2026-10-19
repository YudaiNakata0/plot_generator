#!/usr/bin/env python3
"""誤差 NPZ の r / theta の RMS を計算する。

使い方:
    ./scripts/calculate_rms.py
    ./scripts/calculate_rms.py stats/errors/*_errors.npz
    ./scripts/calculate_rms.py stats/errors/*.npz --output stats/rms.csv

現在の誤差 NPZ で使われている ``error_r`` / ``error_theta`` と、
旧形式の ``r`` / ``theta`` のどちらにも対応する。
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def _find_key(data, names, path):
    for name in names:
        if name in data:
            return name
    joined = " / ".join(repr(name) for name in names)
    raise KeyError(f"{path} does not contain {joined}")


def _unit(data, key, default):
    if "__meta__" not in data:
        return default
    try:
        info = json.loads(str(data["__meta__"]))
        return info.get("units", {}).get(key, default)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def rms(values, path, key):
    values = np.asarray(values, dtype=float).ravel()
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError(f"{path}: {key} contains no finite values")
    return float(np.sqrt(np.mean(values**2)))


def calculate_file(path):
    """Return one file's path, RMS values, and units."""
    with np.load(path, allow_pickle=False) as data:
        r_key = _find_key(data, ("error_r", "r"), path)
        theta_key = _find_key(data, ("error_theta", "theta"), path)
        return {
            "file": str(path),
            "r_rms": rms(data[r_key], path, r_key),
            "theta_rms": rms(data[theta_key], path, theta_key),
            "r_unit": _unit(data, r_key, "m"),
            "theta_unit": _unit(data, theta_key, "rad"),
        }


def _input_files(values):
    if not values:
        values = [Path("stats/errors")]

    files = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            files.extend(sorted(path.glob("*.npz")))
        elif path.exists():
            files.append(path)
        else:
            raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")
    if not files:
        raise FileNotFoundError("対象となる NPZ ファイルがありません")
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="誤差 NPZ の r / theta の RMS を計算します")
    parser.add_argument(
        "npz_files",
        nargs="*",
        type=Path,
        help="NPZ ファイルまたはディレクトリ（省略時: stats/errors）",
    )
    parser.add_argument("-o", "--output", type=Path, help="結果を CSV に保存")
    args = parser.parse_args(argv)

    results = [calculate_file(path) for path in _input_files(args.npz_files)]
    print(f"{'file':<60} {'RMS r':>14} {'RMS theta':>14}")
    for result in results:
        print(
            f"{result['file']:<60} "
            f"{result['r_rms']:>14.6g} {result['theta_rms']:>14.6g}"
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["file", "r_rms", "r_unit", "theta_rms", "theta_unit"])
            for result in results:
                writer.writerow(
                    [
                        result["file"],
                        result["r_rms"],
                        result["r_unit"],
                        result["theta_rms"],
                        result["theta_unit"],
                    ]
                )
        print(f"saved: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
