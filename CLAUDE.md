# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code 向けのガイドです。

## 開発の目的

rosbag (`.bag`) などのデータファイルから様々なグラフを作成する **GUI アプリケーション** を `app/main.py` に開発する。
`scripts/` には過去に個別に作ったデータ処理・可視化スクリプトがあり、これらの機能をアプリケーションに統合していくことがゴール。

- 基本的に作業対象は `app/` 配下。
- `scripts/` は機能・仕様の参考実装として読む（原則として変更しない）。
- `bags/`, `data/`, `camera_images/`, `figures/`, `result/`, `storage/` はスクリプト実行の副産物（入力データ・出力ファイル）なので、確認する必要はない。

## 実行環境

- Python 3.10、ROS1（ROS One: `/opt/ros/one`）。`rosbag`, `roslib`, `rospy`, `geometry_msgs`, `cv_bridge` は ROS の環境から import する。
- 主な依存ライブラリ: `numpy`, `matplotlib`, `scipy`, `opencv-python (cv2)`, `tkinter`。
- パッケージ管理ファイル（requirements.txt 等）やテスト・リンタ設定は無い。
- スクリプトは実行権限付きで、リポジトリのトップディレクトリから実行する前提（相対パスは `os.getcwd()` 基準で解決される）。

```bash
./app/main.py                                  # アプリ起動
./scripts/plot_Pose.py bags/xxx.bag /topic     # 既存スクリプトの例
```

## app/main.py の現状（開発初期段階）

tkinter + matplotlib による GUI。現状の流れ:

1. `MainWindow` がウィンドウ・キャンバス・「OPEN FILE」「RESET」ボタンを配置
2. 「OPEN FILE」→ `filedialog` で bag ファイルを選択し、トピック一覧と型 (`topic_types`) を取得
3. `SelectionDialog`（Listbox ダイアログ）でトピックを選択
4. `roslib.message.get_message_class` でメッセージクラスを取得し、`build_msg_tree` でフィールド一覧（`pose.position.x` のようなドット区切り）を作って再度選択

まだグラフ描画までは実装されていない（フィールド選択後は `print("result:", ...)` するだけ）。

注意点:

- `build_msg_tree` はメッセージ型の配列フィールド（例: `geometry_msgs/Point[]`）を `get_message_class` が `None` を返すためスキップする。プリミティブ配列（`float64[]` 等）はそのままフィールドとして列挙される。
- 独自メッセージ型（`spinal/*`, `aerial_robot_msgs/*` など）は、その型のパッケージがビルド・source されていないと `get_message_class` が `None` になり、フィールドを列挙できない。

## scripts/ の概要（アプリに持たせたい機能）

README.md にも主要スクリプトのオプション説明がある。各スクリプトは argparse で引数を受け取り、`plt.show()` で表示するスタイル。

### rosbag → グラフ / npz 変換

| スクリプト | 入力 | 機能 | 出力 npz |
|---|---|---|---|
| `plot_Pose.py` | bag + Pose 型トピック | xyz の時系列（目標値の線 `axhline`・許容範囲の帯 `axhspan`）、roll/pitch/yaw の時系列。`-s/-e` で時間切り出し、`--ox/--oy/--oz` で軸ごとに非表示 | `data/endeffector_pose_*.npz`（time, x, y, z, tx, ty, tz, roll, pitch, yaw, troll, tpitch, tyaw） |
| `record_orientation.py` | bag + Pose 型トピック | 目標姿勢（RPY）とのクォータニオン差から姿勢誤差角 θ = 2·arccos(dq.w) を計算・プロット | `data/endeffector_orientation_error_*.npz`（time, theta） |
| `record_WrenchStamped.py` | bag + WrenchStamped 型トピック | 力 (force x/y/z) の時系列。構造は plot_Pose.py とほぼ同じ（関数名も `plot_Pose` のまま） | `data/wrench_force_*.npz`（time, x, y, z, tx, ty, tz） |
| `image_extractor.py` | bag + Image 型トピック | 指定区間・間隔で画像を PNG 保存（cv_bridge） | 画像ファイル |

共通処理: 時刻はメッセージ受信時刻 `t.to_sec()` を先頭 0 に揃える。時間切り出し後も再度 0 始まりにする。

### npz → グラフ

| スクリプト | 必要なキー | 機能 |
|---|---|---|
| `plot_from_npz.py` | time, x, y, z, tx, ty, tz | xyz 3 段の時系列プロット（目標線・範囲帯） |
| `draw_trajectory.py` | time, x, y, z, tx, ty, tz | 2D 軌跡（`--axis` で法線軸指定、時間で色付けした `LineCollection` + 太い帯、目標円、開始/終了マーカー、カラーバー）、3D 軌跡（`Line3DCollection`、目標円盤）。`-a/-p` で傾いた壁面（pitch 回転）に対応 |
| `boxplot_rad.py` | r | 複数 npz の位置誤差 r の箱ひげ図 |
| `boxplot_orientation_quaternion.py` | theta | 複数 npz の姿勢誤差 θ の箱ひげ図 |
| `boxplot_orientation.py` | roll, pitch, yaw | 実験ごとに RPY を 3 色並べた箱ひげ図 |
| `boxplot_position_orientation.py` | r と theta（別ファイル） | r と θ を左右 2 軸（twinx）でペアにした箱ひげ図 |

箱ひげ図は共通して `whis=[0, 100]`（ひげ = 最小〜最大）、`patch_artist=True`、黒枠、y 方向の破線グリッド、`-o` で保存（dpi=300）、`--noshow` で非表示。

### 誤差計算

- `calculate_error.py`: npz のキー名を指定して各軸の RMS 誤差 / 標準偏差を表示。`-s` で各軸誤差を `*_rpy.npz` に保存。
- `calculate_error_rad.py`: 目標位置とのユークリッド距離 r を計算し `*_r.npz`（time, r）に保存、時系列と箱ひげ図を表示。

### 画像解析

- `result_analyze.py`: 画像の HSV 閾値で黄色領域と非白色領域の面積を求め、割合を表示（OpenCV ウィンドウで可視化）。

### 共通モジュール

- `scripts/module/operation_quaternion.py`: scipy `Rotation` を使ったクォータニオン/オイラー角（`"xyz"`）変換、合成、差分。`geometry_msgs` の `Quaternion` / `Pose` 型を入出力に使う。
## データの流れ

```
.bag ──(plot_Pose / record_* )──> data/*.npz ──(calculate_error*)──> *_r.npz, *_rpy.npz
  │                                   │                                   │
  └─(image_extractor)─> 画像          └─(plot_from_npz / draw_trajectory)  └─(boxplot_*)─> 箱ひげ図
```

単位: 位置 [m]、角度 [rad]、力 [N]、時間 [s]。

## 開発方針・注意

- `scripts/` のコードは重複が多い（軸ごとにコピペ、`if x: float(x) else 0` の繰り返し等）。アプリに取り込む際は「データ読み込み（bag / npz）」「計算処理」「描画」を分けて共通化する。
- 既存スクリプトは引数を文字列で受け取り、`if tx:` のように truthy 判定しているため値 0 が「未指定」扱いになる。アプリでは `None` と 0 を区別する。
- 既存スクリプトの見た目（色、目標線 `C1` alpha=0.5、範囲帯 alpha=0.2、カラーマップ `viridis` など）は論文用の図として調整されたものなので、移植時はなるべく踏襲する。
- コメントは日本語・英語が混在しているので、周囲のコードに合わせる。
- コミットメッセージは `[scripts](ファイル名) 説明` / `[README] 説明` のように、対象ディレクトリ等を角括弧で前置する形式。
