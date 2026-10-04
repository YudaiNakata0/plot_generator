"""メインウィンドウ: 左にデータ、中央にグラフ、右に設定、下にログ。"""
import os

from core.loaders import npz
from core.processing import stats as st

from .dataset_panel import DatasetPanel
from .jobs import JobRunner
from .param_panel import ParamPanel
from .plot_view import DrawSpec, PlotView
from .qt import Qt, QtGui, QtWidgets
from .source_panel import SourcePanel
from .stats_panel import StatsPanel

OPEN_FILTER = "データファイル (*.bag *.npz);;rosbag (*.bag);;npz (*.npz);;すべて (*)"
EXPORT_FILTER = "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)"
PRESET_FILTER = "プリセット (*.json)"


def _load_bag(path, topic, mode, fields, time_source, progress=None):
    # bag.py は ROS 環境が必要なので、使うときに import する
    from core.loaders import bag

    kwargs = dict(time_source=time_source, progress=progress)
    if mode == "pose":
        return bag.load_pose(path, topic, **kwargs)
    if mode == "wrench":
        return bag.load_wrench(path, topic, **kwargs)
    return bag.load(path, topic, fields, **kwargs)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("plot")
        self.resize(1400, 850)
        self._last_dir = os.getcwd()

        self.jobs = JobRunner(self)
        self.sources = SourcePanel(self.jobs)
        self.datasets = DatasetPanel()
        self.params = ParamPanel()
        self.plots = PlotView()
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.stats = StatsPanel()

        # 中央下: ログと統計のタブ
        self.bottom_tabs = QtWidgets.QTabWidget()
        self.bottom_tabs.addTab(self.log_view, "ログ")
        self.bottom_tabs.addTab(self.stats, "統計")

        # ===== layout =====
        left = QtWidgets.QSplitter(Qt.Vertical)
        left.addWidget(self._titled("bag ファイル", self.sources))
        left.addWidget(self._titled("データセット", self.datasets))
        left.setSizes([450, 350])

        center = QtWidgets.QSplitter(Qt.Vertical)
        center.addWidget(self.plots)
        center.addWidget(self.bottom_tabs)
        center.setSizes([650, 200])

        main = QtWidgets.QSplitter(Qt.Horizontal)
        main.addWidget(left)
        main.addWidget(center)
        main.addWidget(self._titled("グラフ設定", self.params))
        main.setSizes([340, 700, 360])
        main.setStretchFactor(1, 1)
        self.setCentralWidget(main)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setMaximumWidth(220)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)

        self._setup_menu()

        # ===== signals =====
        for panel in (self.sources, self.datasets, self.params, self.stats):
            panel.message.connect(self.log)
        self.sources.load_requested.connect(self.load_bag_topic)
        self.datasets.selection_changed.connect(self.params.set_channels)
        self.datasets.save_requested.connect(self.save_dataset)
        self.params.draw_requested.connect(self.draw)
        self.plots.currentChanged.connect(self._on_tab_changed)
        self.stats.refresh_requested.connect(self.refresh_stats)
        self.stats.save_requested.connect(self.save_stats)
        self.jobs.running_changed.connect(self._on_running_changed)
        self.jobs.progress.connect(self._on_progress)

    @staticmethod
    def _titled(title, widget):
        box = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(widget)
        return box

    def _setup_menu(self):
        file_menu = self.menuBar().addMenu("ファイル(&F)")
        self._add_action(file_menu, "開く...", self.open_dialog, QtGui.QKeySequence.Open)
        file_menu.addSeparator()
        self._add_action(file_menu, "プリセットを読み込む...", self.load_preset)
        self._add_action(file_menu, "プリセットを保存...", self.save_preset)
        file_menu.addSeparator()
        self._add_action(file_menu, "終了", self.close, QtGui.QKeySequence.Quit)

        export_menu = self.menuBar().addMenu("書き出し(&E)")
        self._add_action(export_menu, "グラフを画像で保存 (dpi=300)...", self.export_plot,
                         QtGui.QKeySequence.Save)

    def _add_action(self, menu, text, slot, shortcut=None):
        action = QtWidgets.QAction(text, self)
        action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(shortcut)
        menu.addAction(action)
        return action

    # ===== ログ・進捗 =====

    def log(self, text):
        self.log_view.appendPlainText(text)
        self.statusBar().showMessage(text.splitlines()[0], 5000)

    def error(self, text):
        self.log(f"[エラー] {text}")

    def _on_running_changed(self, running):
        self.progress.setVisible(running > 0)
        if running == 0:
            self.progress.reset()
        else:
            # 進捗が来るまでは「処理中」の表示にする
            self.progress.setRange(0, 0)

    def _on_progress(self, done, total):
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)

    # ===== ファイル =====

    def open_dialog(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "開く", self._last_dir, OPEN_FILTER)
        self.open_files(paths)

    def open_files(self, paths):
        for path in paths:
            self._last_dir = os.path.dirname(os.path.abspath(path))
            ext = os.path.splitext(path)[1].lower()
            if ext == ".bag":
                self.sources.add_bag(path)
            elif ext == ".npz":
                try:
                    self.datasets.add_dataset(npz.load(path))
                except Exception as e:
                    self.error(f"npz を読み込めません: {path}\n{e}")
            else:
                self.error(f"対応していない形式です: {path}")

    def load_bag_topic(self, path, topic, mode, fields, time_source):
        self.log(f"読み込み開始: {os.path.basename(path)} {topic}")
        self.jobs.submit(
            _load_bag, path, topic, mode, fields, time_source,
            with_progress=True,
            on_done=self.datasets.add_dataset,
            on_error=lambda msg: self.error(f"読み込みに失敗: {topic}\n{msg}"),
        )

    def save_dataset(self, dataset):
        default = os.path.join(self._last_dir, dataset.name.replace("/", "_").replace(":", "_") + ".npz")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "npz として保存", default, "npz (*.npz)")
        if not path:
            return
        try:
            npz.save(dataset, path)
        except Exception as e:
            self.error(f"保存できません: {path}\n{e}")
        else:
            self.log(f"保存しました: {path}")

    # ===== 描画 =====

    def draw(self, new_tab=False):
        datasets = self.datasets.checked_datasets()
        channels = self.datasets.checked_channels()
        if not datasets or not channels:
            self.error("データセットとチャンネルにチェックを付けてください")
            return
        plot_type = self.params.plot_type
        spec = DrawSpec(plot_type, datasets, channels, self.params.values())
        tab = self.plots.new_tab(plot_type.name) if new_tab else self.plots.current_tab()
        try:
            tab.draw_plot(spec)
        except Exception as e:
            self.error(f"描画できません: {type(e).__name__}: {e}")
            return
        self.plots.setTabText(self.plots.indexOf(tab), plot_type.name)
        self.log(f"描画: {plot_type.name} / {', '.join(ds.name for ds in datasets)} / {', '.join(channels)}")
        self.update_stats(spec)

    # ===== 統計 =====

    def update_stats(self, spec):
        """spec のデータ・設定値で統計量を計算して表示する。"""
        if spec is None:
            self.stats.set_stats([], "グラフを描画すると、描画したデータの統計量を表示します")
            return
        try:
            params = spec.plot_type.resolve_params(spec.params)
            start, end = params.get("start"), params.get("end")
            results = st.dataset_stats(
                spec.datasets, spec.channels,
                targets=params.get("targets"), bands=params.get("bands"),
                use_file_target=params.get("use_file_target", True),
                start=start, end=end,
            )
        except Exception as e:
            self.error(f"統計量を計算できません: {type(e).__name__}: {e}")
            return
        note = f"{spec.plot_type.name} の設定で計算"
        if start is not None or end is not None:
            note += f"（区間 {'' if start is None else start} 〜 {'' if end is None else end} s）"
        self.stats.set_stats(results, note)

    def refresh_stats(self):
        datasets = self.datasets.checked_datasets()
        channels = self.datasets.checked_channels()
        if not datasets or not channels:
            self.error("データセットとチャンネルにチェックを付けてください")
            return
        self.update_stats(DrawSpec(self.params.plot_type, datasets, channels, self.params.values()))
        self.bottom_tabs.setCurrentWidget(self.stats)

    def _on_tab_changed(self, index):
        # グラフのタブを切り替えたら、そのグラフの統計量を表示する
        tab = self.plots.widget(index)
        if tab is not None:
            self.update_stats(tab.spec)

    def save_stats(self):
        if not self.stats.stats:
            self.error("保存する統計量がありません")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "統計量を CSV で保存", os.path.join(self._last_dir, "stats.csv"), "CSV (*.csv)")
        if not path:
            return
        try:
            st.save_csv(self.stats.stats, path)
        except Exception as e:
            self.error(f"保存できません: {path}\n{e}")
        else:
            self.log(f"保存しました: {path}")

    def export_plot(self):
        tab = self.plots.current_tab()
        if tab.spec is None:
            self.error("まだ何も描画されていません")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "グラフを保存", os.path.join(self._last_dir, "figure.png"), EXPORT_FILTER)
        if not path:
            return
        try:
            tab.export(path)
        except Exception as e:
            self.error(f"保存できません: {path}\n{e}")
        else:
            self.log(f"保存しました: {path}")

    # ===== プリセット =====

    def save_preset(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "プリセットを保存", self._last_dir, PRESET_FILTER)
        if path:
            self.params.save_preset(path)
            self.log(f"プリセットを保存しました: {path}")

    def load_preset(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "プリセットを読み込む", self._last_dir, PRESET_FILTER)
        if not path:
            return
        try:
            self.params.load_preset(path)
        except Exception as e:
            self.error(f"プリセットを読み込めません: {path}\n{e}")
        else:
            self.log(f"プリセットを読み込みました: {path}")

    def closeEvent(self, event):
        # 読み込み中のスレッドが終わるのを待ってから閉じる
        if self.jobs.running:
            self.log("読み込み中の処理の終了を待っています...")
            self.jobs.wait()
        super().closeEvent(event)
