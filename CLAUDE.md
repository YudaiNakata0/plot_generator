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
- 主な依存ライブラリ: `numpy`, `matplotlib`（apt の 3.5.1）, `scipy`, `opencv-python (cv2)`, `PyQt5`（apt の 5.15）。
- パッケージ管理ファイル（requirements.txt 等）やテスト・リンタ設定は無い。
- スクリプトは実行権限付きで、リポジトリのトップディレクトリから実行する前提（相対パスは `os.getcwd()` 基準で解決される）。

```bash
./app/main.py [bag / npz ...]                  # アプリ起動（引数のファイルを開く）
./scripts/plot_Pose.py bags/xxx.bag /topic     # 既存スクリプトの例
```

## 残作業・ドキュメント

- 今後の作業は `TODO.md` にまとめている。作業を始める前に確認し、終わったらチェックを付ける・新しい課題を追記する。
- 利用者向けの使い方は `USAGE.md`。**アプリの機能を追加・変更・削除したら、同じ作業の中で `USAGE.md` も更新する**（画面の操作、設定項目、統計の列、ショートカットなど利用者から見える変更すべて）。
- `README.md` は `scripts/` の説明。

## app/ の構成

GUI ライブラリは PyQt5（apt の 5.15）を使う方針。Qt6 系は matplotlib 3.5.1 と組み合わせると動かず、cv2 も Qt5 でビルドされているため。npz を基本の保存形式とする。

```
app/
  main.py            # 起動スクリプト（QApplication + MainWindow）
  core/              # GUI 非依存
    dataset.py       # Dataset: name, time, channels{名前: 配列}, units, meta。操作は新しい Dataset を返す
    loaders/
      bag.py         # list_topics / list_fields / load(パス文字列でフィールド指定) / load_pose / load_wrench
      npz.py         # load / save（scripts/ の npz と互換。付随情報は "__meta__" キーに JSON）
    processing/
      stats.py       # 統計量（平均, 標準偏差, 中央値, 最小/最大, 目標値との誤差・RMSE, 範囲内の割合）, CSV 保存
      error.py       # 誤差チャンネル: 各軸の誤差, 位置誤差 r, 姿勢誤差 θ（roll/pitch/yaw → クォータニオン → 回転角）。目標値 0 を meta に設定
      transform.py   # 座標変換 p' = R_軸(角度)·(p − 原点)。接尾辞付きチャンネルと変換後の目標値を追加（draw_trajectory.py の -a -p と一致）
  plots/             # グラフ種類。fig に描くだけで、ファイル読込や plt.show() はしない
    base.py          # Param, PlotType, REGISTRY, @register
    style.py         # scripts/ から引き継いだ色・透明度・箱ひげ図の設定
    timeseries.py    # 時系列（plot_Pose / plot_from_npz / record_WrenchStamped を統合）
    trajectory2d.py  # 2D 軌跡（draw_trajectory.py の 2D から、時間で色付けした線・目標円・マーカー・カラーバー）
  gui/               # PyQt5
    qt.py            # Qt の import を集約（QT_API=pyqt5 を指定。Qt6 移行時はここを差し替える）
    jobs.py          # JobRunner: 別スレッドで処理し、コールバックはメインスレッドで呼ぶ
    main_window.py   # 左: bag / データセット、中央: グラフタブ + ログ / 統計、右: グラフ設定
    source_panel.py  # bag → トピック → フィールドのツリー。チェックしたフィールドを読み込む
    dataset_panel.py # Dataset → チャンネルのツリー。チェックしたものを描画に使う
    param_panel.py   # PlotType.params から入力欄を自動生成。プリセット（JSON）の保存・読み込み
    plot_view.py     # グラフのタブ（キャンバス + ツールバー）。書き出しは figsize・dpi=300 で描き直す
    stats_panel.py   # 中央下「統計」タブ。描画のたびに、そのグラフの設定値（targets/bands/start/end）で再計算
    error_dialog.py  # 誤差計算のダイアログ（データセットの右クリック）。結果は DatasetPanel.replace_dataset で差し替え
    transform_dialog.py # 座標変換のダイアログ（データセットの右クリック）。結果は DatasetPanel.replace_dataset で差し替え
```

- `app/` から `import core` / `import plots` する前提（`./app/main.py` 実行時は `app/` が sys.path に入る）。
- `core/loaders/bag.py` は ROS 環境が必要。`core/loaders/__init__.py` では import しない。
- bag の meta["target"] に入る目標値は npz の命名（`tx`, `troll` など = `"t" + チャンネル名`）。チャンネルの目標値は `Dataset.target_for(channel)` で引く。
- Dataset にチャンネルを足す処理（座標変換など）は、新しい Dataset を作って `DatasetPanel.replace_dataset(id, ds)` で差し替える（チャンネルのチェック状態は名前で引き継がれる）。変換の記録は meta["transforms"] に残す。
- 統計は PlotType の params のうち `targets`, `bands`, `use_file_target`, `start`, `end` を（あれば）使う。新しいグラフ種類でも同じ意味ならこのキー名にそろえる。
- 新しいグラフ種類は `plots/` に `PlotType` のサブクラスを作り `@register` し、`plots/__init__.py` で import する。
  使うチャンネル数は `channel_count = (最小, 最大)` で宣言し、`check_channels(datasets, channels, self.channel_count)` で検査する。
- カラーバーを付ける図は `fig.set_constrained_layout(True)` を使う（`PlotTab` は描画前に constrained_layout を解除し、constrained_layout の図ではリサイズ時の tight_layout をしない）。
- bag の読み込みは大きい bag だと数秒以上かかる（0deg.bag の 277 メッセージのトピックで約 5 秒）。GUI では別スレッドで呼ぶ。
- GUI から bag を読むなど時間のかかる処理は `JobRunner.submit` で実行する。ワーカースレッドから Qt のウィジェットを触らない。
- matplotlib 3.5.1 にはフォントのフォールバックが無いので、日本語を含む文字列には `plots/style.py` の `font_kwargs` / `legend_kwargs` を使う（英語だけの図は DejaVu Sans のまま）。
- 描画の確認は `QT_QPA_PLATFORM=offscreen` で `MainWindow` を作って操作し、`window.grab().save(...)` で画面を保存して見る。

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
