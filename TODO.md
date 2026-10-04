# TODO

`app/` の GUI アプリ開発の残作業。別のデバイスで作業を再開するときはここから確認する。
設計の詳細は `CLAUDE.md` を参照。作業が終わったらチェックを付け、新しい課題は追記する。
機能を追加・変更したら、利用者向けの `USAGE.md` も合わせて更新する。

## 進め方（全体の手順）

- [x] 手順1: `core/`（Dataset, bag/npz の読み込み）と時系列プロット
- [x] 手順2: PyQt5 の GUI の骨組み（3 列レイアウト、入力欄の自動生成、画像保存、プリセット、別スレッドでの bag 読み込み）
- [ ] 手順3: 派生チャンネルと統計（統計は完了）
- [ ] 手順4: 箱ひげ図、軌跡（2D は完了。次は座標変換で傾いた壁面に対応）
- [ ] 手順5: 画像ツール（bag からの画像書き出し、色面積の解析）

## 手順3: 派生チャンネルと統計

- [ ] `core/processing/quaternion.py`: qx, qy, qz, qw から roll / pitch / yaw（scipy `Rotation`, `"xyz"`）。`geometry_msgs` に依存しない numpy 配列版
- [ ] 姿勢誤差 θ = 2·arccos(|dq.w|)（目標 RPY を入力）。`record_orientation.py` 相当
  - 既存スクリプトは `arccos(dq.w)` で符号を考慮していない。q と -q が同じ姿勢なので `abs` を取るべきか確認する
- [ ] 位置誤差 r（目標位置とのユークリッド距離）。`calculate_error_rad.py` 相当
- [ ] 各軸の誤差（x - tx など）。`calculate_error.py` 相当
- [ ] GUI: データセットの右クリックメニューから派生チャンネルを追加するダイアログ（目標値の入力欄付き）
- [x] 統計: `core/processing/stats.py` と中央下の「統計」タブ（平均, 標準偏差, 中央値, 最小/最大, 平均誤差, RMSE, 最大誤差, 範囲内の割合）。コピー・CSV 保存
- [ ] 統計: 派生チャンネル（r, θ, 各軸の誤差）ができたら、それらの統計も確認する
- [ ] 目標値を Dataset の meta["target"] に設定・編集する UI（npz に保存されるように）

## 手順4: 箱ひげ図、軌跡

- [ ] `plots/boxplot.py`: `boxplot_rad.py`, `boxplot_orientation_quaternion.py`, `boxplot_orientation.py`, `boxplot_position_orientation.py` を 1 つに統合
  - 複数 Dataset × 選択チャンネル。チャンネルごとの色、左右 2 軸（twinx）のオプション
  - 見た目は `plots/style.py` の `BOXPLOT`, `GRID_Y` を使う
- [x] `plots/trajectory2d.py`: 2D 軌跡（時間で色付けした線、目標円、開始/終了マーカー、カラーバー、横軸の反転、縦横の入れ替え）。複数のデータセットは横に並べ、縮尺と時間の色の範囲を揃える
- [x] `PlotType.channel_count` で使うチャンネル数を宣言し、数が合わないとエラーにする
- [ ] **（次にやる）座標変換** `core/processing/transform.py`: 傾いた壁面（`draw_trajectory.py` の `-a/-p`）への対応
  - 回転の軸・角度・回転の中心（目標位置）を指定し、変換したチャンネル（`y'`, `z'` など）を Dataset に追加する。軌跡だけでなく時系列・統計でも使える
  - 目標値も同じ変換をかけて meta["target"] に入れる（変換後の目標円の中心が原点などになるように）
  - GUI: データセットの右クリック →「座標変換...」。手順3の派生チャンネルと同じ仕組みにする
  - 元のスクリプトでは回転行列 R_y(pitch) を目標位置からの相対座標にかけている（`draw_trajectory.py` の 2D）。3D の目標円盤の回転は -0.2 rad 固定だった
- [ ] 軌跡の帯を実寸の幅 [m] で描く（エンドエフェクタやツールの大きさを表す意図。元のスクリプトの線幅 18 の帯は画面上の太さだった）
- [ ] 壁を真横から見た図: 「目標の形: 円 / 線分」の設定（`draw_trajectory.py` の `--axis y` の分岐）
- [ ] 3D 軌跡（`plots/trajectory3d.py`）: チャンネル 3 つ、目標円盤、書き出し用の視点（仰角・方位角）の設定
- [ ] 軌跡の凡例が小さいパネルで軌跡に重なる。凡例の位置の設定か、図の外に出す方法を検討

## 手順5: 画像ツール

- [ ] `image_extractor.py` 相当: Image トピックから区間・間隔を指定して PNG 書き出し（別スレッド）
- [ ] `result_analyze.py` 相当: HSV 閾値で黄色 / 非白色の面積比。表示は `cv2.imshow` ではなく Qt で行う（将来 Qt6 にしたとき cv2 の Qt5 と混ざらないように）

## GUI の改善

- [ ] 異なる bag の同じトピックをまとめて読み込む（実験の比較用。例: 0deg, 10deg, -10deg の endeffector_pose）
- [ ] bag の読み込み結果を npz にキャッシュして、2 回目以降を速くする
- [ ] データセットのチャンネル名の変更（`Dataset.rename`）を GUI から
- [ ] Dataset の時間の切り出しを GUI から（今はグラフ設定の開始・終了のみ）
- [ ] ドラッグ&ドロップでファイルを開く
- [ ] 最近開いたファイル、ウィンドウ配置の保存（QSettings）
- [ ] プリセットにデータセット・チャンネルの選択も含めるか検討（今はグラフの種類と設定値のみ）
- [ ] 書き出しサイズ（figsize）を GUI で指定できるようにする（今は PlotType.figsize の値）
- [ ] 長いデータセット名（`0deg:/gimbalrotor/endeffector_pose`）が凡例で長すぎる。読み込み時の既定の名前を短くするか検討
- [ ] 実際のディスプレイでの操作確認（ここまでの確認は `QT_QPA_PLATFORM=offscreen` で行った）

## 既知の制限・注意

- matplotlib 3.5.1 はフォントのフォールバックが無い。日本語を含む文字列にだけ日本語フォント（IPAexGothic など）を使う処理を `plots/style.py` に入れている。新しいグラフ種類でもタイトル・凡例などに `style.font_kwargs` / `style.legend_kwargs` を使う
- matplotlib 3.5.1 と Qt6（PySide6 6.11）は組み合わせると動かない。`gui/qt.py` で `QT_API=pyqt5` を指定している
- 大きい bag の読み込みは遅い（0deg.bag の 277 メッセージのトピックで約 5 秒）
- 長さ 33 以上の配列フィールド（covariance, 画像の data など）はフィールド一覧に出ない（`core/loaders/bag.py` の `MAX_ARRAY_LENGTH`）

## 別デバイスでの環境構築メモ

- Ubuntu 22.04, Python 3.10, ROS1（ROS One: `/opt/ros/one`）
- `sudo apt install python3-pyqt5`（PyQt5 5.15）。matplotlib は apt の 3.5.1 で動作確認済み
- 日本語フォント: `fonts-ipaexfont` か `fonts-noto-cjk`
- 起動: リポジトリのトップで `./app/main.py [ファイル ...]`
- GUI を表示せずに確認するとき: `QT_QPA_PLATFORM=offscreen` を付けて、`MainWindow` を作って操作し `window.grab().save("x.png")` で画面を保存する
