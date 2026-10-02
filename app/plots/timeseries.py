"""時系列プロット。

scripts/plot_Pose.py, plot_from_npz.py, record_WrenchStamped.py の時系列グラフを統合したもの。
任意のチャンネルを縦に並べる (subplots) か 1 つのグラフに重ねる (overlay)。
"""
import numpy as np

from . import style
from .base import Param, PlotType, check_channels, register

# データの線の色。C1 は目標値の色なので使わない
DATA_COLORS = ["C0", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"]


def _file_targets(datasets, channel):
    """Dataset の meta["target"] から目標値を探す（npz の tx, troll などの命名規則）。"""
    values = []
    for ds in datasets:
        targets = ds.targets
        for key in ("t" + channel, channel):
            if key in targets and targets[key] not in values:
                values.append(targets[key])
                break
    return values


@register
class TimeSeriesPlot(PlotType):
    name = "時系列"
    description = "チャンネルの時間変化。目標値の線と許容範囲の帯を描ける"
    params = [
        Param("targets", float, label="目標値", per_channel=True),
        Param("bands", float, label="許容範囲 (±)", per_channel=True),
        Param("use_file_target", bool, True, label="ファイルの目標値を使う",
              help="目標値が未入力のチャンネルは、npz の tx などの値を使う"),
        Param("start", float, label="開始", unit="s"),
        Param("end", float, label="終了", unit="s"),
        Param("layout", str, "subplots", label="配置", choices=("subplots", "overlay"),
              help="subplots: チャンネルごとに縦に並べる / overlay: 1 つに重ねる"),
        Param("y_half_range", float, label="縦軸の表示範囲 (中心±)",
              help="指定するとデータの中心 ± この値を表示する"),
        Param("share_y_scale", bool, False, label="縦軸の幅を揃える",
              help="全グラフの縦軸の幅を、一番変動の大きいチャンネルに揃える"),
        Param("min_y_half_range", float, label="縦軸の最小表示範囲 (中心±)"),
        Param("legend", bool, True, label="凡例を表示"),
        Param("title", str, label="タイトル"),
    ]

    def figsize(self, datasets, channels, params):
        if params["layout"] == "overlay":
            return (8, 4)
        return (8, 3 * len(channels))

    def draw(self, fig, datasets, channels, params):
        params = self.resolve_params(params)
        check_channels(datasets, channels)
        if params["start"] is not None or params["end"] is not None:
            datasets = [ds.crop(params["start"], params["end"]) for ds in datasets]

        if params["layout"] == "overlay":
            ax = fig.subplots(1, 1)
            groups = [(ax, list(channels))]
        else:
            axes = fig.subplots(len(channels), 1, sharex=True, squeeze=False)[:, 0]
            groups = [(ax, [channel]) for ax, channel in zip(axes, channels)]

        multi = len(datasets) > 1
        color_index = 0
        for ax, group in groups:
            if params["layout"] == "subplots":
                # グラフごとに同じ Dataset が同じ色になるようにする
                color_index = 0
            for channel in group:
                for ds in datasets:
                    if multi and len(group) > 1:
                        label = f"{ds.name} {channel}"
                    elif multi:
                        label = ds.name
                    else:
                        label = channel
                    color = DATA_COLORS[color_index % len(DATA_COLORS)]
                    ax.plot(ds.time, ds[channel], label=label, color=color)
                    color_index += 1
                self._draw_target(ax, datasets, channel, params)

            ax.set_ylabel(self._ylabel(datasets, group))
            if params["legend"]:
                ax.legend()

        groups[-1][0].set_xlabel("Time [s]")
        self._set_ylim(datasets, groups, params)
        if params["title"]:
            fig.suptitle(params["title"])
        fig.tight_layout()

    @staticmethod
    def _draw_target(ax, datasets, channel, params):
        if channel in params["targets"]:
            targets = [params["targets"][channel]]
        elif params["use_file_target"]:
            targets = _file_targets(datasets, channel)
        else:
            targets = []
        band = params["bands"].get(channel)
        for target in targets:
            ax.axhline(target, **style.TARGET_LINE)
            if band is not None:
                ax.axhspan(target - band, target + band, **style.TARGET_BAND)

    @staticmethod
    def _ylabel(datasets, group):
        units = {ds.unit(channel) for ds in datasets for channel in group}
        unit = units.pop() if len(units) == 1 else ""
        text = ", ".join(group)
        return f"{text} [{unit}]" if unit else text

    @staticmethod
    def _set_ylim(datasets, groups, params):
        centers = []
        half_spans = []
        for _, group in groups:
            values = np.concatenate([ds[channel] for ds in datasets for channel in group])
            vmax, vmin = np.nanmax(values), np.nanmin(values)
            centers.append((vmax + vmin) * 0.5)
            half_spans.append((vmax - vmin) * 0.5 * 1.05)

        if params["y_half_range"] is not None:
            halves = [params["y_half_range"]] * len(groups)
        elif params["share_y_scale"] or params["min_y_half_range"] is not None:
            halves = half_spans
            if params["share_y_scale"]:
                halves = [max(half_spans)] * len(groups)
            if params["min_y_half_range"] is not None:
                halves = [max(h, params["min_y_half_range"]) for h in halves]
        else:
            # matplotlib の自動調整に任せる
            return

        for (ax, _), center, half in zip(groups, centers, halves):
            if half > 0:
                ax.set_ylim(center - half, center + half)
