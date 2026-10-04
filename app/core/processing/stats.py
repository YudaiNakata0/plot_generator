"""チャンネルの統計量。

scripts/calculate_error.py（各軸の RMS 誤差 / 標準偏差）に相当する計算を、
任意の Dataset・チャンネルについて行う。NaN は除いて計算する。
"""
from __future__ import annotations

import csv
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChannelStats:
    dataset: str
    channel: str
    unit: str
    count: int            # NaN を除いた点数
    duration: float       # 計算に使った区間の長さ [s]
    mean: float
    std: float            # 標準偏差（母標準偏差, np.std と同じ）
    median: float
    min: float
    max: float
    target: float | None = None
    bias: float | None = None           # 平均 - 目標値
    rmse: float | None = None           # sqrt(mean((v - 目標値)^2))
    max_abs_error: float | None = None  # max |v - 目標値|
    band: float | None = None
    within_band: float | None = None    # |v - 目標値| <= band の割合 (0〜1)


# (属性名, 表示名) 表と CSV の列
COLUMNS = [
    ("dataset", "データセット"),
    ("channel", "チャンネル"),
    ("unit", "単位"),
    ("count", "点数"),
    ("duration", "区間 [s]"),
    ("mean", "平均"),
    ("std", "標準偏差"),
    ("median", "中央値"),
    ("min", "最小"),
    ("max", "最大"),
    ("target", "目標値"),
    ("bias", "平均誤差"),
    ("rmse", "RMSE"),
    ("max_abs_error", "最大誤差"),
    ("band", "許容範囲 (±)"),
    ("within_band", "範囲内の割合 [%]"),
]


def channel_stats(time, values, target=None, band=None, dataset="", channel="", unit=""):
    """1 チャンネル分の統計量を計算する。target が None なら誤差系の値は None。"""
    values = np.asarray(values, dtype=float)
    time = np.asarray(time, dtype=float)
    valid = ~np.isnan(values)
    v = values[valid]
    if len(v) == 0:
        nan = float("nan")
        return ChannelStats(dataset, channel, unit, 0, 0.0, nan, nan, nan, nan, nan,
                            target=target, band=band)

    result = dict(
        dataset=dataset, channel=channel, unit=unit,
        count=int(len(v)),
        duration=float(time[valid][-1] - time[valid][0]),
        mean=float(np.mean(v)),
        std=float(np.std(v)),
        median=float(np.median(v)),
        min=float(np.min(v)),
        max=float(np.max(v)),
    )
    if target is not None:
        error = v - target
        result.update(
            target=float(target),
            bias=float(np.mean(error)),
            rmse=float(np.sqrt(np.mean(error ** 2))),
            max_abs_error=float(np.max(np.abs(error))),
        )
        if band is not None:
            result.update(band=float(band), within_band=float(np.mean(np.abs(error) <= band)))
    elif band is not None:
        result["band"] = float(band)
    return ChannelStats(**result)


def dataset_stats(datasets, channels, targets=None, bands=None, use_file_target=True,
                  start=None, end=None):
    """複数の Dataset × チャンネルの統計量を計算する。

    targets / bands: {チャンネル名: 値}。targets に無いチャンネルは use_file_target なら
    Dataset の meta["target"]（tx など）を使う。
    start / end: 計算に使う区間 [s]（時系列プロットの開始・終了と同じ意味）。
    データセットに無いチャンネルは飛ばす。
    """
    targets = targets or {}
    bands = bands or {}
    results = []
    for ds in datasets:
        if start is not None or end is not None:
            ds = ds.crop(start, end)
        for channel in channels:
            if channel not in ds:
                continue
            target = targets.get(channel)
            if target is None and use_file_target:
                target = ds.target_for(channel)
            results.append(channel_stats(
                ds.time, ds[channel], target, bands.get(channel),
                dataset=ds.name, channel=channel, unit=ds.unit(channel),
            ))
    return results


def display_value(stats, attr):
    """表示用の値（割合は % にする）。None はそのまま返す。"""
    value = getattr(stats, attr)
    if attr == "within_band" and value is not None:
        return value * 100
    return value


def format_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, np.integer)):
        return str(value)
    return f"{value:.6g}"


def to_table(stats_list, formatted=True):
    """[[ヘッダ...], [行...], ...] を返す（CSV・クリップボード用）。"""
    rows = [[label for _, label in COLUMNS]]
    for stats in stats_list:
        row = [display_value(stats, attr) for attr, _ in COLUMNS]
        rows.append([format_value(v) for v in row] if formatted else row)
    return rows


def save_csv(stats_list, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        # utf-8-sig: Excel で開いても日本語が化けないように BOM を付ける
        csv.writer(f).writerows(to_table(stats_list, formatted=False))
