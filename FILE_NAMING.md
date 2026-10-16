# File Naming Rules

このリポジトリで使っている `figures/trajectory` と `stats/` の命名規則を、他のスクリプトや別リポジトリでも再利用しやすいように整理したメモです。

## 変数

- `run_id`: 実験実行時刻の文字列。例: `2026-09-18-11-17-34`
- `experiment_id`: `parameters/<run_id>.json` のファイル名から拡張子を除いたもの
- `stem`: グラフや統計の系列を表す短い識別子。例: `d7_0deg_1`, `filament_d5_0deg_1`
- `wall_angle`: 壁角度。例: `0`, `10`, `-20`
- `diameter`: 目標径を表す短い識別子。通常系では `d5`, `d7`, `d10`, `d14` のように使う

## 通常系

通常の自動生成物は、次の形でそろっています。

- 画像: `figures/trajectory/{stem}_trajectory_{run_id}.png`
- 統計: `stats/{stem}_xyz_{run_id}.csv`

ここで `stem` は実験条件を圧縮した名前です。

- 例: `d7_0deg_1_trajectory_2026-09-18-11-17-34.png`
- 例: `d7_0deg_1_xyz_2026-09-18-11-17-34.csv`

### `stem` の作り方

現行データでは、次のような部品をつないでいます。

- `d{diameter}`: 目標径
- `{wall_angle}deg`: 壁角度
- `{trial}`: 同一条件内の通し番号 `1`, `2`, `3`, ...
- 必要に応じて先頭や末尾に補助ラベルを入れる。例: `filament_d5_0deg_1`

### 覚えておく点

- `experiment_id` はそのまま `run_id` として末尾に入れるのが基本です。
- `stats` 側の `xyz` は、`x/y/z` の3軸統計であることを示す固定ラベルです。
- 画像と CSV は同じ `run_id` を共有し、あとから対応付けできるようにしています。

## 使い回すときの指針

- 条件をあとから追跡したいなら、ファイル名に `run_id` を残す
- 条件差を比較したいなら、`stem` か `[...]` の部分に実験条件を集約する
- 新しい出力形式を増やすときも、`{series}_{condition}_{run_id}` か `[series][condition]{run_id}` のどちらかに寄せると整理しやすい