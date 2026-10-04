"""中央: グラフのタブ。各タブは matplotlib キャンバスとツールバーを持つ。"""
from dataclasses import dataclass

from matplotlib.figure import Figure

from plots.style import SAVE_DPI

from .qt import FigureCanvasQTAgg, NavigationToolbar2QT, QtWidgets


@dataclass
class DrawSpec:
    """タブに描いた内容（書き出し時に同じ内容を描き直すため）。"""
    plot_type: type
    datasets: list
    channels: list
    params: dict


class PlotTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.spec = None
        # ウィンドウサイズが変わっても余白が崩れないようにする
        self.canvas.mpl_connect("resize_event", self._on_resize)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

    def draw_plot(self, spec):
        self.figure.clear()
        # constrained_layout はグラフの種類ごとに draw() の中で設定する
        self.figure.set_constrained_layout(False)
        try:
            spec.plot_type().draw(self.figure, spec.datasets, spec.channels, spec.params)
        except Exception:
            self.figure.clear()
            self.canvas.draw_idle()
            raise
        self.spec = spec
        self.canvas.draw_idle()

    def export(self, path):
        """プロット種類の推奨サイズ・dpi=300 で描き直して保存する（ウィンドウサイズに依存しない）。"""
        if self.spec is None:
            raise ValueError("まだ何も描画されていません")
        spec = self.spec
        plot = spec.plot_type()
        params = spec.plot_type.resolve_params(spec.params)
        figure = Figure(figsize=plot.figsize(spec.datasets, spec.channels, params))
        plot.draw(figure, spec.datasets, spec.channels, spec.params)
        figure.savefig(path, dpi=SAVE_DPI)

    def _on_resize(self, event):
        if self.figure.axes and not self.figure.get_constrained_layout():
            try:
                self.figure.tight_layout()
            except ValueError:
                pass


class PlotView(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self._close_tab)
        self.new_tab()

    def new_tab(self, title="グラフ"):
        tab = PlotTab()
        self.setCurrentIndex(self.addTab(tab, title))
        return tab

    def current_tab(self):
        return self.currentWidget()

    def _close_tab(self, index):
        widget = self.widget(index)
        self.removeTab(index)
        widget.deleteLater()
        if self.count() == 0:
            self.new_tab()
