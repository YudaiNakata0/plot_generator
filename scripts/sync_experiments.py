#!/usr/bin/env python3
"""Synchronize experiment metadata into plot parameter JSON files.

The YAML file is the editable source of truth.  The ``experiment`` object in
each JSON file is deliberately retained as a snapshot so that edits made to a
JSON file can be detected instead of silently overwritten.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by installation errors
    raise SystemExit("PyYAML が必要です: python3-yaml をインストールしてください") from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YAML = ROOT / "experiments_description.yaml"
DEFAULT_PARAMETERS = ROOT / "parameters"
DEFAULT_STATE = ROOT / ".experiment_sync.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSONのルートはオブジェクトにしてください")
    return value


def _read_yaml(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream) or {}
    experiments = document.get("experiments") if isinstance(document, dict) else None
    if not isinstance(experiments, dict):
        raise ValueError(f"{path}: experiments オブジェクトが必要です")
    result: dict[str, dict[str, Any]] = {}
    for experiment_id, value in experiments.items():
        if not isinstance(experiment_id, str) or not isinstance(value, dict):
            raise ValueError(f"{path}: 実験IDと実験情報はオブジェクトにしてください")
        _validate_experiment(experiment_id, value)
        result[experiment_id] = copy.deepcopy(value)
    return result


def _validate_experiment(experiment_id: str, experiment: dict[str, Any]) -> None:
    required = ("target_diameter", "wall_angle", "task_start", "task_end", "target_position")
    missing = [key for key in required if key not in experiment]
    position = experiment.get("target_position")
    if missing or not isinstance(position, dict) or any(axis not in position for axis in ("x", "y", "z")):
        details = ", ".join(missing) if missing else "target_position の x/y/z"
        raise ValueError(f"{experiment_id}: 必須項目がありません ({details})")


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "experiments": {}}
    value = _read_json(path)
    experiments = value.get("experiments", {})
    if not isinstance(experiments, dict):
        raise ValueError(f"{path}: experiments オブジェクトが必要です")
    return {"version": 1, "experiments": experiments}


def _parameter_files(parameters_dir: Path) -> dict[str, Path]:
    return {path.stem: path for path in parameters_dir.glob("*.json")}


def _template_path(files: dict[str, Path]) -> Path:
    if not files:
        raise ValueError("YAMLにだけ存在する実験を生成するためのJSONテンプレートがありません")
    return files[sorted(files)[0]]


def _synced_config(config: dict[str, Any], experiment: dict[str, Any]) -> dict[str, Any]:
    """Return a config with only the YAML-owned fields changed."""
    result = copy.deepcopy(config)
    result["experiment"] = copy.deepcopy(experiment)

    position = experiment["target_position"]
    wall_angle = experiment["wall_angle"]
    target = {axis: position[axis] for axis in ("x", "y", "z")}
    plot = result.setdefault("plot", {})
    plot_params = plot.setdefault("params", {})
    plot_params["start"] = experiment["task_start"]
    plot_params["end"] = experiment["task_end"]
    plot_params["diameter"] = experiment["target_diameter"] / 1000

    if "statistics" in result:
        statistics = result["statistics"]
        if isinstance(statistics, str):
            statistics = {"path": statistics}
            result["statistics"] = statistics
        if not isinstance(statistics, dict):
            raise ValueError("statistics はオブジェクトまたはパス文字列にしてください")
        statistics_params = statistics.setdefault("params", {})
        statistics_params["targets"] = copy.deepcopy(target)

    if wall_angle == 0:
        plot["channels"] = ["y", "z"]
        plot_params["targets"] = {"y": position["y"], "z": position["z"]}
        if result.get("inputs") and isinstance(result["inputs"][0], dict):
            result["inputs"][0].pop("transform", None)
    else:
        plot["channels"] = ["y'", "z'"]
        plot_params["targets"] = {"y'": 0, "z'": 0}
        inputs = result.get("inputs")
        if not isinstance(inputs, list) or not inputs or not isinstance(inputs[0], dict):
            raise ValueError("inputs[0] がないため wall_angle の transform を設定できません")
        inputs[0]["transform"] = {
            "channels": ["x", "y", "z"],
            "origin": [position["x"], position["y"], position["z"]],
            "axis": "y",
            "angle": wall_angle * 0.02,
            "suffix": "'",
        }
    return result


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _write_state(path: Path, state: dict[str, Any]) -> None:
    _write_json(path, state)


def synchronize(
    yaml_path: Path = DEFAULT_YAML,
    parameters_dir: Path = DEFAULT_PARAMETERS,
    state_path: Path = DEFAULT_STATE,
    experiment_id: str | None = None,
    check: bool = False,
    force: bool = False,
) -> int:
    yaml_experiments = _read_yaml(yaml_path)
    files = _parameter_files(parameters_dir)
    state = _load_state(state_path)
    old_snapshots = state["experiments"]
    selected = {experiment_id} if experiment_id else set(yaml_experiments) | set(files)
    unknown = selected - set(yaml_experiments) - set(files)
    if unknown:
        raise ValueError(f"指定された実験が見つかりません: {', '.join(sorted(unknown))}")

    actions: list[tuple[str, str, Path | None, dict[str, Any] | None]] = []
    conflicts: list[str] = []
    unsynced = False
    for current_id in sorted(selected):
        yaml_experiment = yaml_experiments.get(current_id)
        path = files.get(current_id)
        if yaml_experiment is None:
            print(f"警告: JSONにだけ存在する実験です: {current_id}", file=sys.stderr)
            continue
        yaml_digest = _hash(yaml_experiment)
        if path is None:
            template = _read_json(_template_path(files))
            updated = _synced_config(template, yaml_experiment)
            actions.append(("create", current_id, parameters_dir / f"{current_id}.json", updated))
            unsynced = True
            continue

        config = _read_json(path)
        if "experiment" not in config or not isinstance(config["experiment"], dict):
            raise ValueError(f"{path}: experiment オブジェクトがありません")
        current_json_experiment = config["experiment"]
        json_digest = _hash(current_json_experiment)
        expected = _synced_config(config, yaml_experiment)
        derived_changed = config != expected
        previous = old_snapshots.get(current_id)
        if previous is None:
            # Bootstrap is safe only when the existing snapshot already agrees
            # with YAML.  A differing pair has no trustworthy baseline.
            yaml_changed = False
            json_changed = False
            initial_mismatch = yaml_digest != json_digest
        else:
            yaml_changed = yaml_digest != previous.get("yaml_hash")
            json_changed = json_digest != previous.get("json_hash")
            initial_mismatch = False

        if initial_mismatch or (yaml_changed and json_changed):
            if force:
                print(f"強制同期: {current_id}", file=sys.stderr)
            else:
                conflicts.append(current_id)
                print(f"競合: {current_id} (YAMLとJSONの両方が変更されています)", file=sys.stderr)
                continue
        elif json_changed and not yaml_changed:
            print(f"警告: JSON側だけが変更されています。上書きしません: {current_id}", file=sys.stderr)
            continue
        elif not yaml_changed and not json_changed and not derived_changed:
            continue

        updated = expected
        actions.append(("update", current_id, path, updated))
        unsynced = True

    if conflicts:
        print("同期を中止しました。--force でYAMLを優先できます。", file=sys.stderr)
        return 1
    if check:
        for action, current_id, path, _ in actions:
            print(f"未同期: {action} {current_id} -> {path}")
        return 1 if unsynced else 0

    new_state = {"version": 1, "experiments": copy.deepcopy(old_snapshots)}
    for action, current_id, path, updated in actions:
        assert path is not None and updated is not None
        _write_json(path, updated)
        print(f"{action}: {path}")
        new_state["experiments"][current_id] = {
            "yaml_hash": _hash(yaml_experiments[current_id]),
            "json_hash": _hash(updated["experiment"]),
        }
    # Record unchanged, successfully compared entries too.  JSON-only changes
    # intentionally retain their old snapshot so the warning is repeated.
    for current_id in sorted(set(yaml_experiments) & set(files) & selected):
        if current_id not in new_state["experiments"]:
            config = _read_json(files[current_id])
            new_state["experiments"][current_id] = {
                "yaml_hash": _hash(yaml_experiments[current_id]),
                "json_hash": _hash(config.get("experiment", {})),
            }
    _write_state(state_path, new_state)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="experiments_description.yaml を parameters/*.json に同期します")
    parser.add_argument("--check", action="store_true", help="変更せず、未同期状態だけ確認する")
    parser.add_argument("--force", action="store_true", help="競合時もYAMLの実験情報で上書きする")
    parser.add_argument("--id", dest="experiment_id", help="指定した実験だけ同期する")
    parser.add_argument("--yaml", type=Path, default=DEFAULT_YAML, help=argparse.SUPPRESS)
    parser.add_argument("--parameters", type=Path, default=DEFAULT_PARAMETERS, help=argparse.SUPPRESS)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.check and args.force:
        print("--check と --force は同時に指定できません", file=sys.stderr)
        return 2
    try:
        return synchronize(args.yaml, args.parameters, args.state, args.experiment_id, args.check, args.force)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"sync-experiments: エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
