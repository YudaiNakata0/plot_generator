#!/usr/bin/env bash
set -euo pipefail

# このスクリプトはリポジトリの場所を基準に設定・出力を扱う。
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# JSONの内容が前回の成功時から変わったものだけplot_cliに渡す。
exec python3 - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


STATE_PATH = Path(".generate_plots_and_stats.json")


def load_state():
    if not STATE_PATH.exists():
        return {}

    try:
        with STATE_PATH.open(encoding="utf-8") as stream:
            state = json.load(stream)
        if not isinstance(state, dict) or any(
            not isinstance(path, str) or not isinstance(digest, str)
            for path, digest in state.items()
        ):
            raise ValueError("state is not a path-to-hash mapping")
        return state
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"Warning: {STATE_PATH} を読み込めないため、全件処理します: {exc}",
            file=sys.stderr,
        )
        return {}


def save_state(state):
    """状態ファイルを一時ファイル経由で置き換える。"""
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=STATE_PATH.parent,
            prefix=f".{STATE_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(state, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary_path, STATE_PATH)
    except Exception:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass
        raise


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    configs = sorted(Path("parameters").glob("*.json"))
    if not configs:
        print("No parameter JSON files found in parameters/", flush=True)
        return 0

    previous_state = load_state()
    next_state = {}
    processed = 0
    skipped = 0
    failed = []

    for config_path in configs:
        config_name = config_path.as_posix()
        current_digest = digest(config_path)

        if previous_state.get(config_name) == current_digest:
            print(f"Skipping unchanged: {config_name}", flush=True)
            next_state[config_name] = current_digest
            skipped += 1
            continue

        print(f"Processing: {config_name}", flush=True)
        result = subprocess.run(
            [sys.executable, "app/plot_cli.py", str(config_path)],
            check=False,
        )
        if result.returncode == 0:
            next_state[config_name] = current_digest
            processed += 1
        else:
            print(
                f"Failed: {config_name} (exit status {result.returncode})",
                file=sys.stderr,
            )
            failed.append(config_name)

    try:
        save_state(next_state)
    except OSError as exc:
        print(f"Warning: {STATE_PATH} を保存できません: {exc}", file=sys.stderr)
        return 1

    print(
        f"Done: processed={processed}, skipped={skipped}, failed={len(failed)}",
        flush=True,
    )
    return 1 if failed else 0


raise SystemExit(main())
PY
