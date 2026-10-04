"""中央下「統計」タブ: 描画したデータの統計量の表。

描画するたびに、そのグラフの設定（目標値・許容範囲・開始/終了）で計算し直す。
"""
from core.processing import stats as st

from .qt import Qt, QtWidgets, Signal

# 数値の列（右寄せにする）
_TEXT_COLUMNS = {"dataset", "channel", "unit"}


class StatsPanel(QtWidgets.QWidget):
    refresh_requested = Signal()
    save_requested = Signal()
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats = []

        self.note = QtWidgets.QLabel("グラフを描画すると、描画したデータの統計量を表示します")
        self.note.setWordWrap(True)

        self.table = QtWidgets.QTableWidget(0, len(st.COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in st.COLUMNS])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        # 最初は描画した順に並べ、見出しをクリックしたときだけ並べ替える
        self.table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.table.setSortingEnabled(True)

        refresh = QtWidgets.QPushButton("今の選択で再計算")
        refresh.setToolTip("チェックしたデータセット・チャンネルと、右の設定値で計算し直す")
        refresh.clicked.connect(self.refresh_requested)
        copy = QtWidgets.QPushButton("コピー")
        copy.setToolTip("表をタブ区切りでクリップボードにコピー（Excel などに貼り付けられる）")
        copy.clicked.connect(self.copy_to_clipboard)
        save = QtWidgets.QPushButton("CSV で保存...")
        save.clicked.connect(self.save_requested)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.note, 1)
        buttons.addWidget(refresh)
        buttons.addWidget(copy)
        buttons.addWidget(save)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(buttons)
        layout.addWidget(self.table, 1)

    @property
    def stats(self):
        return list(self._stats)

    def set_stats(self, stats_list, note=""):
        self._stats = list(stats_list)
        self.note.setText(note)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.table.setRowCount(len(self._stats))
        for row, stats in enumerate(self._stats):
            for col, (attr, _) in enumerate(st.COLUMNS):
                value = st.display_value(stats, attr)
                item = QtWidgets.QTableWidgetItem()
                if attr in _TEXT_COLUMNS or value is None:
                    item.setText(st.format_value(value))
                else:
                    # 数値として並べ替えられるように DisplayRole に数値を入れ、表示は桁を揃える
                    item.setData(Qt.DisplayRole, float(st.format_value(value)))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self._hide_empty_columns()

    def _hide_empty_columns(self):
        """目標値などが 1 つも無い列は隠す。"""
        for col, (attr, _) in enumerate(st.COLUMNS):
            empty = all(getattr(s, attr) is None for s in self._stats)
            self.table.setColumnHidden(col, empty and attr not in _TEXT_COLUMNS)

    def copy_to_clipboard(self):
        if not self._stats:
            self.message.emit("コピーする統計量がありません")
            return
        rows = st.to_table(self._stats)
        text = "\n".join("\t".join(row) for row in rows)
        QtWidgets.QApplication.clipboard().setText(text)
        self.message.emit(f"統計量をクリップボードにコピーしました ({len(self._stats)} 行)")
