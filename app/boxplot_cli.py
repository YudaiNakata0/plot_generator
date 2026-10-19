#!/usr/bin/env python3
"""複数の誤差時系列NPZから、実験ごとの r / theta 箱ひげ図を作るCLI。"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# matplotlib 3.5.1 は QT_API 未指定時に PyQt6 / PySide6 を優先することが
# あり、Qt5Agg と Qt6 の enum API が合わず import に失敗する。
# GUI アプリと同じく、Qt を使う経路では PyQt5 を明示する。
os.environ.setdefault("QT_API", "pyqt5")

import matplotlib

import numpy as np


def _label(path, data):
    if "__meta__" in data:
        try:
            info = json.loads(str(data["__meta__"]))
            meta = info.get("meta", {})
            if meta.get("experiment"):
                return str(meta["experiment"])
            if info.get("name"):
                return str(info["name"])
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return os.path.splitext(os.path.basename(path))[0]


def _position_error_in_mm(path, data):
    """Return ``error_r`` in mm, regardless of the NPZ's stored unit.

    Older error files store the position error in metres, while newer files
    may store it in millimetres.  Use the unit recorded in ``__meta__`` so the
    plotted values always agree with the axis label.
    """
    r = np.asarray(data["error_r"], dtype=float).ravel()
    unit = "m"
    if "__meta__" in data:
        try:
            info = json.loads(str(data["__meta__"]))
            unit = info.get("units", {}).get("error_r", "m")
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    if unit == "m":
        return r * 1000.0
    if unit == "mm":
        return r
    raise ValueError(f"{path}: unsupported error_r unit {unit!r}; expected 'm' or 'mm'")


def _pyplot(show):
    """表示の有無に合わせてMatplotlibのバックエンドを選ぶ。"""
    # pyplot を import する前にバックエンドを選ぶ必要がある。
    # --noshow ではディスプレイ不要の Agg を使い、通常実行では
    # PyQt5 と接続する Qt5Agg を使って plt.show() を有効にする。
    backend = "Qt5Agg" if show else "Agg"
    matplotlib.use(backend, force=True)
    import matplotlib.pyplot as plt

    return plt


def create_boxplot(npz_files, output=None, show=True):
    plt = _pyplot(show)
    r_data, theta_data, labels = [], [], []
    for path in npz_files:
        with np.load(path) as data:
            for key in ("error_r", "error_theta"):
                if key not in data:
                    raise KeyError(f"{path} does not contain key '{key}'")
            r = _position_error_in_mm(path, data)
            theta = np.asarray(data["error_theta"], dtype=float).ravel()
            if len(r) == 0 or len(theta) == 0:
                raise ValueError(f"{path} contains an empty error array")
            r = r[np.isfinite(r)]
            theta = theta[np.isfinite(theta)]
            if len(r) == 0 or len(theta) == 0:
                raise ValueError(f"{path} contains no finite error values")
            r_data.append(r)
            theta_data.append(theta)
            labels.append(_label(path, data))

    count = len(labels)
    figure, ax_r = plt.subplots(figsize=(2.2 * count, 5))
    ax_theta = ax_r.twinx()
    r_positions = [2.0 * i + 0.8 for i in range(count)]
    theta_positions = [2.0 * i + 1.6 for i in range(count)]
    xticks = [2.0 * i + 1.2 for i in range(count)]
    box_style = dict(
        widths=0.6,
        whis=[0, 100],
        showfliers=True,
        patch_artist=True,
        boxprops=dict(linewidth=1.2, edgecolor="black"),
        medianprops=dict(linewidth=1.0, color="black"),
        whiskerprops=dict(linewidth=1.2, color="black"),
        capprops=dict(linewidth=1.2, color="black"),
    )
    bp_r = ax_r.boxplot(r_data, positions=r_positions, **box_style)
    bp_theta = ax_theta.boxplot(theta_data, positions=theta_positions, **box_style)
    for box in bp_r["boxes"]:
        box.set_facecolor("#92b1d9")
    for box in bp_theta["boxes"]:
        box.set_facecolor("#f6c8b6")
    ax_r.set_xticks(xticks)
    ax_r.set_xticklabels(labels, rotation=30, ha="right")
    ax_r.set_ylabel("Position Error r [mm]")
    ax_theta.set_ylabel("Orientation Error θ [rad]")
    ax_r.set_ylim(bottom=0)
    ax_theta.set_ylim(bottom=0)
    ax_r.grid(True, axis="y", linestyle="--", alpha=0.5)
    figure.tight_layout()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, dpi=300)
    if show:
        plt.show()
    plt.close(figure)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="誤差NPZから r / theta の箱ひげ図を作ります")
    parser.add_argument("npz_files", nargs="+", type=Path, help="*_errors.npz")
    parser.add_argument("-o", "--output", type=Path, help="出力画像")
    parser.add_argument("--noshow", action="store_true", help="画面表示しない")
    args = parser.parse_args(argv)
    output = create_boxplot(args.npz_files, args.output, show=not args.noshow)
    if output is not None:
        print(f"saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
