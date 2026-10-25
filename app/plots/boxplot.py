"""Dataset ごとのチャンネル分布を比較する箱ひげ図。"""
from __future__ import annotations

from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator
import numpy as np

from . import style
from .base import Param, PlotType, check_channels, register


# チャンネルごとに同じ色を使う。選択数が増えても循環して描画できる。
BOX_COLORS = [
    "#92b1d9",
    "#f6c8b6",
    "#b7d7a8",
    "#d9b3e6",
    "#f3d58a",
    "#a9d9d0",
]


@register
class BoxPlot(PlotType):
    name = "箱ひげ図"
    description = "複数データセットのチャンネル分布を箱ひげ図で比較する"
    params = [
        Param(
            "axis",
            str,
            label="Y軸",
            choices=("left", "right"),
            per_channel=True,
            help="チャンネルごとに左軸または右軸へ割り当てる。既定は左軸",
        ),
        Param("start", float, label="開始", unit="s"),
        Param("end", float, label="終了", unit="s"),
        Param(
            "left_tick",
            float,
            label="左軸の目盛り間隔",
            help="空欄なら自動。0以下は指定できません",
        ),
        Param(
            "right_tick",
            float,
            label="右軸の目盛り間隔",
            help="空欄なら自動。0以下は指定できません",
        ),
        Param("left_min", float, 0.0, label="左軸の下限"),
        Param("right_min", float, 0.0, label="右軸の下限"),
        Param(
            "left_max",
            float,
            label="左軸の上限",
            help="空欄ならデータに合わせて自動。下限より大きい値を指定してください",
        ),
        Param(
            "right_max",
            float,
            label="右軸の上限",
            help="空欄ならデータに合わせて自動。下限より大きい値を指定してください",
        ),
        Param(
            "box_width",
            float,
            1.0,
            label="箱の横幅倍率",
            help="箱の横幅を既定値に対する倍率で指定する。正の値を指定してください",
        ),
        Param(
            "x_labels",
            str,
            label="横軸のラベル",
            help="データセット順にカンマ区切りで指定。空欄ならデータセット名",
        ),
        Param("x_title", str, label="横軸のタイトル"),
        Param("left_title", str, label="左縦軸のタイトル"),
        Param("right_title", str, label="右縦軸のタイトル"),
        Param("left_legend", str, label="左軸の凡例"),
        Param("right_legend", str, label="右軸の凡例"),
        Param("title", str, label="タイトル"),
    ]

    def figsize(self, datasets, channels, params):
        return (max(6.0, 2.2 * len(datasets)), 5.0)

    def draw(self, fig, datasets, channels, params):
        params = self.resolve_params(params)
        check_channels(datasets, channels, self.channel_count)
        if not datasets:
            raise ValueError("データセットを1つ以上選んでください")

        if params["start"] is not None or params["end"] is not None:
            datasets = [ds.crop(params["start"], params["end"]) for ds in datasets]

        axis_by_channel = {
            channel: params["axis"].get(channel, "left") for channel in channels
        }
        self._validate_units(datasets, channels, axis_by_channel)

        has_left = any(axis_by_channel[ch] == "left" for ch in channels)
        has_right = any(axis_by_channel[ch] == "right" for ch in channels)
        ax_left = fig.subplots(1, 1)
        ax_right = ax_left.twinx() if has_left and has_right else None
        axes = {"left": ax_left, "right": ax_right or ax_left}

        group_width = max(len(channels), 1) + 1.0
        positions = {
            channel: [group_width * i + j + 1 for i in range(len(datasets))]
            for j, channel in enumerate(channels)
        }
        if params["box_width"] <= 0:
            raise ValueError("箱の横幅倍率は0より大きくしてください")
        box_width = min(0.7, 0.8 / len(channels)) * params["box_width"]
        box_style = dict(style.BOXPLOT, widths=box_width)

        for channel_index, channel in enumerate(channels):
            values = []
            for dataset in datasets:
                data = np.asarray(dataset[channel], dtype=float).ravel()
                data = data[np.isfinite(data)]
                if len(data) == 0:
                    raise ValueError(
                        f"{dataset.name}: チャンネル '{channel}' に有限な値がありません"
                    )
                values.append(data)

            axis_name = axis_by_channel[channel]
            result = axes[axis_name].boxplot(
                values,
                positions=positions[channel],
                **box_style,
            )
            color = BOX_COLORS[channel_index % len(BOX_COLORS)]
            for box in result["boxes"]:
                box.set_facecolor(color)

        xticks = [
            group_width * i + (len(channels) + 1) / 2
            for i in range(len(datasets))
        ]
        ax_left.set_xticks(xticks)
        ax_left.set_xticklabels(
            self._x_labels(datasets, params["x_labels"]), rotation=0, ha="center",
            **style.font_kwargs(*(params["x_labels"] or "").split(",")),
        )
        if params["x_title"]:
            ax_left.set_xlabel(
                params["x_title"], **style.font_kwargs(params["x_title"])
            )
        ax_left.set_xlim(0.3, group_width * len(datasets) - 0.3)
        self._set_lower_limit(ax_left, params["left_min"], "左軸")
        self._set_upper_limit(ax_left, params["left_max"], params["left_min"], "左軸")
        if ax_right is not None:
            self._set_lower_limit(ax_right, params["right_min"], "右軸")
            self._set_upper_limit(
                ax_right, params["right_max"], params["right_min"], "右軸"
            )
            self._configure_ticks(
                ax_left,
                ax_right,
                params["left_tick"],
                params["right_tick"],
                params["left_min"],
                params["right_min"],
            )
        elif params["left_tick"] is not None:
            self._set_tick_interval(ax_left, params["left_tick"], params["left_min"])

        for axis_name, axis in (("left", ax_left), ("right", ax_right)):
            if axis is None:
                continue
            selected = [ch for ch in channels if axis_by_channel[ch] == axis_name]
            axis_title = params[f"{axis_name}_title"]
            axis_label = axis_title or self._axis_label(datasets, selected)
            axis.set_ylabel(axis_label, **style.font_kwargs(axis_label))
            axis.grid(True, **style.GRID_Y)

        handles = [
            Patch(
                facecolor=BOX_COLORS[i % len(BOX_COLORS)],
                edgecolor="black",
                label=(
                    params[f"{axis_by_channel[channel]}_legend"]
                    or channel
                ),
            )
            for i, channel in enumerate(channels)
        ]
        legend_axis = ax_left if has_left else ax_right
        font = style.font_kwargs(*channels)
        legend_axis.legend(handles=handles, prop={"family": font["fontfamily"]})

        if params["title"]:
            fig.suptitle(params["title"], **style.font_kwargs(params["title"]))

        # 書き出し時は表示中のウィンドウに対する resize/tight_layout が
        # 走らないため、長い軸ラベルが図の外へ出ないよう余白を固定する。
        # 特に右軸ラベル (例: "Orientation error [rad]") と、下側の
        # x 軸ラベル (例: "Wall angles [deg]") を収めるための設定。
        fig.subplots_adjust(left=0.16, right=0.82, bottom=0.24, top=0.90)

    @staticmethod
    def _validate_units(datasets, channels, axis_by_channel):
        for axis_name in ("left", "right"):
            axis_channels = [
                channel for channel in channels if axis_by_channel[channel] == axis_name
            ]
            if not axis_channels:
                continue
            units = {dataset.unit(channel) for dataset in datasets for channel in axis_channels}
            if len(units) > 1:
                raise ValueError(
                    f"{axis_name}軸に異なる単位のチャンネルがあります: "
                    f"{sorted(units)}。チャンネルの軸を分けてください"
                )

    @staticmethod
    def _axis_label(datasets, channels):
        units = {dataset.unit(channel) for dataset in datasets for channel in channels}
        unit = next(iter(units), "")
        label = ", ".join(channels)
        return f"{label} [{unit}]" if unit else label

    @staticmethod
    def _x_labels(datasets, value):
        """横軸のラベルをデータセット数に合わせて解決する。"""
        if not value:
            return [dataset.name for dataset in datasets]
        labels = [label.strip() for label in value.replace("、", ",").split(",")]
        if len(labels) != len(datasets) or any(not label for label in labels):
            raise ValueError(
                "横軸のラベルはデータセット数と同じ個数を、カンマ区切りで指定してください"
            )
        return labels

    @staticmethod
    def _align_tick_positions(ax_left, ax_right):
        """左右の表示範囲を保ったまま、主目盛りの高さだけ揃える。

        左軸の目盛りを表示範囲内の相対位置に変換し、その位置を右軸の
        表示範囲へ写像する。これにより、例えば左軸の1刻みと右軸の0.1刻みを
        同じ高さに置きつつ、左右で異なる単位・数値範囲を維持できる。
        """
        left_min, left_max = ax_left.get_ylim()
        right_min, right_max = ax_right.get_ylim()
        if left_max <= left_min or right_max <= right_min:
            return

        left_ticks = np.asarray(ax_left.get_yticks(), dtype=float)
        margin = (left_max - left_min) * 1e-9
        left_ticks = left_ticks[
            (left_ticks >= left_min - margin) & (left_ticks <= left_max + margin)
        ]
        if len(left_ticks) < 2:
            return

        fractions = (left_ticks - left_min) / (left_max - left_min)
        right_ticks = right_min + fractions * (right_max - right_min)
        ax_right.yaxis.set_major_locator(FixedLocator(right_ticks))

    @classmethod
    def _configure_ticks(
        cls,
        ax_left,
        ax_right,
        left_interval,
        right_interval,
        left_min,
        right_min,
    ):
        """目盛り間隔を設定し、左右の主目盛りの高さを揃える。"""
        cls._validate_tick_interval(left_interval, "左軸")
        cls._validate_tick_interval(right_interval, "右軸")

        if left_interval is None and right_interval is None:
            cls._align_tick_positions(ax_left, ax_right)
            return

        if left_interval is not None:
            cls._set_tick_interval(ax_left, left_interval, left_min)
        if right_interval is not None:
            cls._set_tick_interval(ax_right, right_interval, right_min)

        if left_interval is not None and right_interval is not None:
            # 両方の指定間隔を保ちつつ、同じ数の区間にして目盛り線を揃える。
            left_count = cls._tick_count(ax_left, left_min, left_interval)
            right_count = cls._tick_count(ax_right, right_min, right_interval)
            count = max(left_count, right_count)
            ax_left.set_ylim(left_min, left_min + count * left_interval)
            ax_right.set_ylim(right_min, right_min + count * right_interval)
            cls._set_tick_interval(ax_left, left_interval, left_min, count)
            cls._set_tick_interval(ax_right, right_interval, right_min, count)
            return

        # 片側だけ指定された場合は、指定側の目盛りを基準にもう一方を
        # 表示範囲へ写像する。指定した数値間隔は変更しない。
        if left_interval is not None:
            cls._align_tick_positions(ax_left, ax_right)
        else:
            cls._align_tick_positions(ax_right, ax_left)

    @staticmethod
    def _set_tick_interval(axis, interval, lower, count=None):
        BoxPlot._validate_tick_interval(interval, "Y")
        if count is None:
            count = BoxPlot._tick_count(axis, lower, interval)
        ticks = lower + np.arange(count + 1, dtype=float) * interval
        axis.yaxis.set_major_locator(FixedLocator(ticks))

    @staticmethod
    def _validate_tick_interval(interval, axis_name):
        if interval is not None and interval <= 0:
            raise ValueError(f"{axis_name}の目盛り間隔は0より大きくしてください")

    @staticmethod
    def _tick_count(axis, lower, interval):
        upper = axis.get_ylim()[1]
        count = int(np.ceil((upper - lower) / interval))
        return max(1, count)

    @staticmethod
    def _set_lower_limit(axis, lower, axis_name):
        upper = axis.get_ylim()[1]
        if upper <= lower:
            raise ValueError(
                f"{axis_name}の下限 {lower:g} がデータの表示範囲を超えています。"
                "下限を小さくしてください"
            )
        axis.set_ylim(lower, upper)

    @staticmethod
    def _set_upper_limit(axis, upper, lower, axis_name):
        if upper is None:
            return
        if upper <= lower:
            raise ValueError(
                f"{axis_name}の上限 {upper:g} は下限 {lower:g} より大きくしてください"
            )
        axis.set_ylim(axis.get_ylim()[0], upper)
