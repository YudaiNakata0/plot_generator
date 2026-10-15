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

from core.loaders import npz
from core.processing import stats as stats_processing
from plots import REGISTRY


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
        return npz.load(path, name=name)
    if kind != "bag":
        raise ValueError(f"未対応の入力形式です: {kind} ({path})")

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
        return bag.load_pose(path, topic, **kwargs)
    if mode == "wrench":
        return bag.load_wrench(path, topic, **kwargs)
    if mode != "fields":
        raise ValueError(f"bag の mode は pose / wrench / fields です: {mode}")
    fields = spec.get("fields")
    if not fields:
        raise ValueError(f"fields mode のbag入力には fields が必要です: {path}")
    return bag.load(path, topic, fields, **kwargs)


def _read_config(config_path):
    with config_path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("設定JSONのトップレベルはオブジェクトにしてください")
    return config


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
        statistics_channels = statistics.get("channels", channels)
        if not isinstance(statistics_channels, list) or not statistics_channels:
            raise ValueError("statistics.channels は統計するチャンネルの配列にしてください")
        statistics_path = _path(statistics["path"], base)
        statistics_path.parent.mkdir(parents=True, exist_ok=True)
        results = stats_processing.dataset_stats(
            datasets,
            statistics_channels,
            targets=resolved.get("targets"),
            bands=resolved.get("bands"),
            use_file_target=resolved.get("use_file_target", True),
            start=resolved.get("start"),
            end=resolved.get("end"),
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
