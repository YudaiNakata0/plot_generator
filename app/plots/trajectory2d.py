"""2D 軌跡。

scripts/draw_trajectory.py の 2D モードから、時間で色付けした軌跡・目標円・開始/終了マーカー・
カラーバーを移植したもの。チェックした 2 チャンネルを横軸・縦軸にする（並び順で先が横軸）。
複数のデータセットは横に並べ、縮尺（表示幅）と時間の色の範囲を揃える。各パネルの中心はそれぞれの目標かデータの中心。

傾いた壁面への回転は座標変換（予定）、実寸の幅の帯・3D は未実装（TODO.md を参照）。
"""
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Circle
from matplotlib.ticker import MultipleLocator

from . import style
from .base import Param, PlotType, check_channels, register

# 自動の表示範囲に付ける余白（データ範囲に対する割合）
MARGIN = 0.05


@register
class Trajectory2DPlot(PlotType):
    name = "軌跡 (2D)"
    description = "2 つのチャンネルを横軸・縦軸にした平面上の軌跡。時間で色分けし、目標円を描ける"
    channel_count = (2, 2)
    params = [
        Param("targets", float, label="目標値（目標円の中心）", per_channel=True),
        Param("use_file_target", bool, True, label="ファイルの目標値を使う",
              help="目標値が未入力のチャンネルは、npz の ty, tz などの値を使う"),
        Param("radius", float, label="目標円の半径", unit="m",
              help="空欄なら目標円を描かない。円の中心には目標値を使う"),
        Param("start", float, label="開始", unit="s"),
        Param("end", float, label="終了", unit="s"),
        Param("half_range", float, label="表示範囲 (中心±)",
              help="表示の中心 ± この値を表示する。空欄なら全データが入るように自動で決める（全パネル共通の幅）"),
        Param("center", str, "目標", label="表示の中心", choices=("目標", "データ"),
              help="各パネルの表示の中心。目標値が無いときはデータの中心になる"),
        Param("tick", float, label="目盛り間隔", help="空欄なら自動"),
        Param("swap", bool, False, label="縦横を入れ替える"),
        Param("invert_x", bool, False, label="横軸を反転",
              help="壁の裏側から見た図にするときなどに使う"),
        Param("markers", bool, True, label="開始・終了のマーカー"),
        Param("colorbar", bool, True, label="カラーバー（時間）"),
        Param("legend", bool, True, label="凡例を表示"),
        Param("title", str, label="タイトル"),
    ]

    def figsize(self, datasets, channels, params):
        return (5 * len(datasets) + 1.5, 5)

    def draw(self, fig, datasets, channels, params):
        params = self.resolve_params(params)
        check_channels(datasets, channels, self.channel_count)
        if params["start"] is not None or params["end"] is not None:
            datasets = [ds.crop(params["start"], params["end"]) for ds in datasets]
        h, v = reversed(channels) if params["swap"] else channels

        fig.set_constrained_layout(True)
        axes = fig.subplots(1, len(datasets), squeeze=False)[0]

        # 全データセットで時間の色の範囲を揃える
        norm = Normalize(min(ds.time.min() for ds in datasets),
                         max(ds.time.max() for ds in datasets))

        lc = None
        centers = []
        for ax, ds in zip(axes, datasets):
            x, y = ds[h], ds[v]
            points = np.array([x, y]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            lc = LineCollection(segments, cmap=style.TIME_CMAP, norm=norm, linewidth=2.0)
            lc.set_array(ds.time[:-1])
            ax.add_collection(lc)

            target = self._target(ds, h, v, params)
            if target is not None and params["radius"] is not None:
                ax.add_patch(Circle(target, params["radius"], label="target area", **style.TARGET_AREA))
            if params["markers"]:
                ax.scatter(x[0], y[0], label="start", **style.START_MARKER)
                ax.scatter(x[-1], y[-1], label="end", **style.END_MARKER)

            ax.set_xlabel(self._label(ds, h))
            ax.set_ylabel(self._label(ds, v))
            ax.set_aspect("equal", adjustable="box")
            ax.grid(True)
            if params["tick"] is not None:
                ax.xaxis.set_major_locator(MultipleLocator(params["tick"]))
                ax.yaxis.set_major_locator(MultipleLocator(params["tick"]))
            if len(datasets) > 1:
                ax.set_title(ds.name, **style.font_kwargs(ds.name))
            if params["legend"] and ax.get_legend_handles_labels()[1]:
                ax.legend(**style.legend_kwargs(ax))

            data_center = ((np.nanmax(x) + np.nanmin(x)) / 2, (np.nanmax(y) + np.nanmin(y)) / 2)
            centers.append(target if params["center"] == "目標" and target is not None else data_center)

        self._set_limits(axes, datasets, h, v, centers, params)

        if params["colorbar"]:
            cbar = fig.colorbar(lc, ax=list(axes))
            cbar.set_label("Time [s]")
        if params["title"]:
            fig.suptitle(params["title"], **style.font_kwargs(params["title"]))

    @staticmethod
    def _target(ds, h, v, params):
        """目標円の中心 (横, 縦)。どちらかが無ければ None。"""
        center = []
        for channel in (h, v):
            value = params["targets"].get(channel)
            if value is None and params["use_file_target"]:
                value = ds.target_for(channel)
            if value is None:
                return None
            center.append(value)
        return tuple(center)

    @staticmethod
    def _label(ds, channel):
        unit = ds.unit(channel)
        return f"{channel} [{unit}]" if unit else channel

    def _set_limits(self, axes, datasets, h, v, centers, params):
        """全パネルを同じ縮尺（同じ表示幅）にし、各パネルはそれぞれの中心で表示する。

        データセットごとに目標位置が大きく違っても、各軌跡が見えるようにするため。
        横軸の反転もここで行う。
        """
        half = params["half_range"]
        if half is None:
            # 各パネルの中心から、データ（と目標円）の一番遠い点までが入る幅を共通にする
            needed = []
            for ds, (cx, cy) in zip(datasets, centers):
                extent = max(np.nanmax(np.abs(ds[h] - cx)), np.nanmax(np.abs(ds[v] - cy)))
                target = self._target(ds, h, v, params)
                if target is not None and params["radius"] is not None:
                    extent = max(extent, abs(target[0] - cx) + params["radius"],
                                 abs(target[1] - cy) + params["radius"])
                needed.append(extent)
            half = max(needed) * (1 + MARGIN) or 1.0

        for ax, (cx, cy) in zip(axes, centers):
            xlim = (cx - half, cx + half)
            ax.set_xlim(*(reversed(xlim) if params["invert_x"] else xlim))
            ax.set_ylim(cy - half, cy + half)
