from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np


@dataclass(frozen=True)
class Dataset:
    """時系列データのまとまり。

    time と channels の各配列は同じ長さ (N,)。
    操作は元の Dataset を変更せず、新しい Dataset を返す。

    meta の主なキー:
        source     : 元ファイルのパス
        topic      : rosbag のトピック名
        start_time : time を 0 に揃える前の先頭時刻 [s]
        target     : 目標値 {チャンネル名などのキー: float}（例: {"tx": 0.1}）
    """

    name: str
    time: np.ndarray
    channels: dict[str, np.ndarray]
    units: dict[str, str] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        time = np.asarray(self.time, dtype=float)
        if time.ndim != 1:
            raise ValueError(f"time must be 1-D, got shape {time.shape}")
        channels = {}
        for key, values in self.channels.items():
            values = np.asarray(values, dtype=float)
            if values.shape != time.shape:
                raise ValueError(
                    f"channel '{key}' has shape {values.shape}, expected {time.shape}"
                )
            channels[key] = values
        # frozen なので object.__setattr__ で正規化した値を入れる
        object.__setattr__(self, "time", time)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "units", dict(self.units))
        object.__setattr__(self, "meta", dict(self.meta))

    def __len__(self):
        return len(self.time)

    def __getitem__(self, key):
        return self.channels[key]

    def __contains__(self, key):
        return key in self.channels

    @property
    def channel_names(self) -> list[str]:
        return list(self.channels.keys())

    @property
    def targets(self) -> dict[str, float]:
        return dict(self.meta.get("target", {}))

    def unit(self, key) -> str:
        return self.units.get(key, "")

    def target_for(self, channel) -> float | None:
        """チャンネルの目標値を meta["target"] から探す（npz の命名規則: x → tx, roll → troll）。"""
        targets = self.meta.get("target", {})
        for key in ("t" + channel, channel):
            if key in targets:
                return targets[key]
        return None

    def crop(self, start=None, end=None, rezero=True) -> Dataset:
        """[start, end] の区間を切り出す。None の端は切らない。rezero で再び 0 始まりにする。"""
        mask = np.ones(len(self.time), dtype=bool)
        if start is not None:
            mask &= self.time >= start
        if end is not None:
            mask &= self.time <= end
        if not mask.any():
            raise ValueError(f"no data in time range [{start}, {end}]")

        time = self.time[mask]
        meta = dict(self.meta)
        if rezero:
            meta["start_time"] = meta.get("start_time", 0.0) + time[0]
            time = time - time[0]
        channels = {key: values[mask] for key, values in self.channels.items()}
        return replace(self, time=time, channels=channels, meta=meta)

    def with_channel(self, key, values, unit="") -> Dataset:
        """チャンネルを追加（同名なら上書き）した Dataset を返す。"""
        channels = dict(self.channels)
        channels[key] = values
        units = dict(self.units)
        if unit:
            units[key] = unit
        return replace(self, channels=channels, units=units)

    def select(self, keys) -> Dataset:
        """指定したチャンネルだけを残す。"""
        missing = [key for key in keys if key not in self.channels]
        if missing:
            raise KeyError(f"{self.name}: no channel {missing}")
        channels = {key: self.channels[key] for key in keys}
        units = {key: self.units[key] for key in keys if key in self.units}
        return replace(self, channels=channels, units=units)

    def rename(self, mapping) -> Dataset:
        """チャンネル名を {旧: 新} で付け替える。"""
        channels = {mapping.get(key, key): values for key, values in self.channels.items()}
        units = {mapping.get(key, key): unit for key, unit in self.units.items()}
        return replace(self, channels=channels, units=units)

    def with_name(self, name) -> Dataset:
        return replace(self, name=name)
