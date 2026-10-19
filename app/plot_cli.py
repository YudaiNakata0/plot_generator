#!/usr/bin/env python3
"""設定JSONから、GUIなしでグラフ画像を書き出すコマンド。

使い方（リポジトリのトップから）::

    python3 app/plot_cli.py path/to/plot.json

このファイルは Qt / GUI モジュールを import しない。入力の読み込みは
``core.loaders``、描画は ``plots`` の既存実装に任せる。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Figure を import する前に非GUIバックエンドを選ぶ。
import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from core.loaders import npz
from core.processing import stats as stats_processing
from core.processing import transform as transform_processing
from plots import REGISTRY, style


def _parser():
    parser = argparse.ArgumentParser(
        description="JSON設定からrosbag/npzのプロット画像をGUIなしで出力します。"
    )
    parser.add_argument("config", type=Path, help="プロット設定JSON")
    parser.add_argument(
        "--debug", action="store_true", help="エラー時にトレースバックを表示する"
    )
    return parser


def _path(value, base):
    path = Path(value).expanduser()
    return path if path.is_absolute() else base / path


def _load_dataset(spec, base):
    if isinstance(spec, str):
        spec = {"path": spec}
    if not isinstance(spec, dict) or "path" not in spec:
        raise ValueError("inputs の各要素には path が必要です")

    path = _path(spec["path"], base)
    kind = spec.get("type", path.suffix.lower().lstrip("."))
    name = spec.get("name")

    if kind == "npz":
        dataset = npz.load(path, name=name)
    elif kind != "bag":
        raise ValueError(f"未対応の入力形式です: {kind} ({path})")
    else:
        # ROS依存のモジュールはbag入力を使うときだけ読み込む。
        from core.loaders import bag

        topic = spec.get("topic")
        if not topic:
            raise ValueError(f"bag入力には topic が必要です: {path}")
        kwargs = {
            "time_source": spec.get("time_source", "receive"),
            "name": name,
        }
        mode = spec.get("mode", "fields")
        if mode == "pose":
            dataset = bag.load_pose(path, topic, **kwargs)
        elif mode == "wrench":
            dataset = bag.load_wrench(path, topic, **kwargs)
        else:
            if mode != "fields":
                raise ValueError(f"bag の mode は pose / wrench / fields です: {mode}")
            fields = spec.get("fields")
            if not fields:
                raise ValueError(f"fields mode のbag入力には fields が必要です: {path}")
            dataset = bag.load(path, topic, fields, **kwargs)

    transform_spec = spec.get("transform")
    if transform_spec is None:
        return dataset
    if not isinstance(transform_spec, dict):
        raise ValueError(f"transform はオブジェクトにしてください: {path}")

    channels = transform_spec.get("channels")
    if not isinstance(channels, list) or len(channels) != 3 or not all(
        isinstance(channel, str) and channel for channel in channels
    ):
        raise ValueError(f"transform.channels は3つのチャンネル名が必要です: {path}")
    missing = [channel for channel in channels if channel not in dataset]
    if missing:
        raise ValueError(f"{path}: transform用チャンネルがありません: {missing}")

    origin_spec = transform_spec.get("origin")
    if origin_spec is None or origin_spec == "none":
        origin = None
    elif origin_spec == "target":
        origin = transform_processing.target_origin(dataset, channels)
        if origin is None:
            raise ValueError(
                f"{path}: transform.origin=target には {channels} の目標値が3つ必要です"
            )
    elif isinstance(origin_spec, list) and len(origin_spec) == 3:
        try:
            origin = [float(value) for value in origin_spec]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"transform.origin は数値3要素が必要です: {path}") from exc
    elif isinstance(origin_spec, list):
        raise ValueError(f"transform.origin は3要素の座標が必要です: {path}")
    else:
        raise ValueError(f"transform.origin は target / none / 3要素配列です: {path}")

    axis = transform_spec.get("axis")
    if axis not in (None, "x", "y", "z"):
        raise ValueError(f"transform.axis は null / x / y / z のいずれかです: {path}")
    suffix = transform_spec.get("suffix", "'")
    if not isinstance(suffix, str) or not suffix:
        raise ValueError(f"transform.suffix は空でない文字列が必要です: {path}")
    try:
        angle = float(transform_spec.get("angle", 0.0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"transform.angle は数値が必要です: {path}") from exc

    return transform_processing.transform_position(
        dataset,
        channels,
        origin=origin,
        axis=axis,
        angle=angle,
        suffix=suffix,
    )


def _read_config(config_path):
    with config_path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("設定JSONのトップレベルはオブジェクトにしてください")
    return config


def _format_trajectory_axes_mm(figure):
    """2D軌跡の位置軸だけ、表示上の単位をmからmmに変える。

    描画データや軸の範囲はmのままにし、目盛り文字列と軸ラベルだけを
    変換する。カラーバーなど、位置軸ではないAxesには適用しない。
    """
    formatter = FuncFormatter(lambda value, _position: f"{value * 1000:g}")
    for axis in figure.axes:
        # 軌跡のAxesには必ず横軸ラベルがあり、カラーバーのAxesにはない。
        if not axis.get_xlabel():
            continue
        axis.xaxis.set_major_formatter(formatter)
        axis.yaxis.set_major_formatter(formatter)
        xlabel = axis.get_xlabel()
        ylabel = axis.get_ylabel()
        if xlabel:
            axis.set_xlabel(xlabel[:-4] + " [mm]" if xlabel.endswith(" [m]") else xlabel + " [mm]")
        if ylabel:
            axis.set_ylabel(ylabel[:-4] + " [mm]" if ylabel.endswith(" [m]") else ylabel + " [mm]")


def _format_trajectory_axis_labels(figure, input_specs):
    """座標変換後の軸ラベルだけ、元のチャンネル名で表示する。

    描画には ``y'`` / ``z'`` などの変換後チャンネルを使うが、CLI出力の
    軸ラベルは論文中の表記に合わせて ``y`` / ``z`` とする。データセットの
    チャンネル名や統計の指定は変更しない。
    """
    renamed = {}
    for spec in input_specs:
        if not isinstance(spec, dict):
            continue
        transform_spec = spec.get("transform")
        if not isinstance(transform_spec, dict):
            continue
        source_channels = transform_spec.get("channels")
        suffix = transform_spec.get("suffix", "'")
        if not isinstance(source_channels, list) or not isinstance(suffix, str):
            continue
        for channel in source_channels:
            if isinstance(channel, str) and channel and suffix:
                renamed[channel + suffix] = channel

    if not renamed:
        return

    def display_label(label):
        for transformed, original in sorted(renamed.items(), key=lambda item: -len(item[0])):
            if label == transformed:
                return original
            prefix = transformed + " "
            if label.startswith(prefix):
                return original + label[len(transformed):]
        return label

    for axis in figure.axes:
        xlabel = axis.get_xlabel()
        ylabel = axis.get_ylabel()
        if xlabel:
            axis.set_xlabel(display_label(xlabel))
        if ylabel:
            axis.set_ylabel(display_label(ylabel))


def _set_titles_times_new_roman(figure):
    """CLI出力では図タイトルを常に Times New Roman にする。

    ``style.font_kwargs`` は日本語やギリシャ文字を含む文字列に日本語
    フォントを選ぶため、実験条件の ``θ`` を含むタイトルも日本語フォント
    になる。CLIで論文用のタイトル書体を揃えるため、描画後にタイトルだけ
    明示的に上書きする。
    """
    if figure._suptitle is not None:
        figure._suptitle.set_fontfamily(style.FONT_FAMILY)
    for axis in figure.axes:
        axis.title.set_fontfamily(style.FONT_FAMILY)


def render(config, config_path):
    """設定を読み込み、画像と指定された統計CSVを書き出す。"""
    base = config_path.parent
    input_specs = config.get("inputs", config.get("datasets"))
    if not input_specs:
        raise ValueError("inputs が空です")
    if not isinstance(input_specs, list):
        raise ValueError("inputs は配列にしてください")

    plot_spec = config.get("plot", {})
    if isinstance(plot_spec, str):
        plot_name = plot_spec
        channels = config.get("channels")
        params = config.get("params", {})
    else:
        plot_name = plot_spec.get("type", plot_spec.get("plot_type"))
        channels = plot_spec.get("channels", config.get("channels"))
        params = plot_spec.get("params", config.get("params", {}))
    if plot_name not in REGISTRY:
        available = ", ".join(REGISTRY)
        raise ValueError(f"未対応のプロット種類です: {plot_name!r}（利用可能: {available}）")
    if not isinstance(channels, list) or not channels:
        raise ValueError("plot.channels に描画するチャンネルの配列が必要です")
    if not isinstance(params, dict):
        raise ValueError("plot.params はオブジェクトにしてください")

    datasets = [_load_dataset(spec, base) for spec in input_specs]
    plot_type = REGISTRY[plot_name]
    resolved = plot_type.resolve_params(params)

    output = config.get("output")
    if isinstance(output, str):
        output = {"path": output}
    if not isinstance(output, dict) or not output.get("path"):
        raise ValueError("output.path が必要です")
    output_path = _path(output["path"], base)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figure = Figure(figsize=plot_type().figsize(datasets, channels, resolved))
    # draw() はGUI版と同じく未解決の入力を受け取り、自身でも解決する。
    plot_type().draw(figure, datasets, channels, params)
    _set_titles_times_new_roman(figure)
    if plot_name == "軌跡 (2D)":
        _format_trajectory_axis_labels(figure, input_specs)
        _format_trajectory_axes_mm(figure)

    save_options = {
        key: output[key]
        for key in ("dpi", "transparent", "bbox_inches", "facecolor", "edgecolor", "format")
        if key in output
    }
    save_options.setdefault("dpi", 300)
    figure.savefig(output_path, **save_options)

    statistics = config.get("statistics", config.get("stats"))
    statistics_path = None
    if statistics is not None:
        if isinstance(statistics, str):
            statistics = {"path": statistics}
        if not isinstance(statistics, dict) or not statistics.get("path"):
            raise ValueError("statistics.path が必要です")
        statistics_params = statistics.get("params", {})
        if not isinstance(statistics_params, dict):
            raise ValueError("statistics.params はオブジェクトにしてください")
        # 統計は既定でプロットと同じ条件を使い、statistics.params があれば
        # 統計専用の条件として上書きする。
        statistics_resolved = plot_type.resolve_params(
            {**params, **statistics_params}
        )
        statistics_channels = statistics.get("channels", channels)
        if not isinstance(statistics_channels, list) or not statistics_channels:
            raise ValueError("statistics.channels は統計するチャンネルの配列にしてください")
        statistics_path = _path(statistics["path"], base)
        statistics_path.parent.mkdir(parents=True, exist_ok=True)
        results = stats_processing.dataset_stats(
            datasets,
            statistics_channels,
            targets=statistics_resolved.get("targets"),
            bands=statistics_resolved.get("bands"),
            use_file_target=statistics_resolved.get("use_file_target", True),
            start=statistics_resolved.get("start"),
            end=statistics_resolved.get("end"),
        )
        stats_processing.save_csv(results, statistics_path)

    return output_path, statistics_path


def main(argv=None):
    args = _parser().parse_args(argv)
    config_path = args.config.expanduser().resolve()
    try:
        output_path, statistics_path = render(_read_config(config_path), config_path)
    except Exception as exc:
        print(f"plot-cli: エラー: {exc}", file=sys.stderr)
        if args.debug:
            raise
        return 1
    print(f"image: {output_path}")
    if statistics_path is not None:
        print(f"statistics: {statistics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
