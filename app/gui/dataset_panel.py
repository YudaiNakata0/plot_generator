"""左下: 読み込んだ Dataset の一覧（Dataset → チャンネル）。

チェックした Dataset と、チェックしたチャンネル（全 Dataset の和集合）をグラフに使う。
Dataset 名はダブルクリックで変更できる（凡例・箱ひげ図のラベルになる）。
"""
import itertools

from .qt import Qt, QtWidgets, Signal

ROLE_ID = Qt.UserRole
ROLE_CHANNEL = Qt.UserRole + 1


class DatasetPanel(QtWidgets.QWidget):
    # チェック状態が変わった（描画に使うチャンネル名のリストを渡す）
    selection_changed = Signal(list)
    save_requested = Signal(object)
    # 座標変換のダイアログを開く（右クリックしたデータセットの ID）
    transform_requested = Signal(int)
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._datasets = {}
        self._ids = itertools.count()

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["データセット", "単位 / 点数"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_menu)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked
                                  | QtWidgets.QAbstractItemView.EditKeyPressed)
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)

    def add_dataset(self, dataset):
        dataset_id = next(self._ids)
        self._datasets[dataset_id] = dataset

        self.tree.blockSignals(True)
        item = QtWidgets.QTreeWidgetItem([dataset.name, f"{len(dataset)} 点"])
        item.setData(0, ROLE_ID, dataset_id)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
        item.setCheckState(0, Qt.Checked)
        self._fill_children(item, dataset, checked=set())
        self.tree.addTopLevelItem(item)
        item.setExpanded(True)
        self.tree.blockSignals(False)

        self.message.emit(f"データセットを追加: {dataset.name} ({len(dataset)} 点, "
                          f"{len(dataset.channel_names)} チャンネル)")
        self.selection_changed.emit(self.checked_channels())

    def replace_dataset(self, dataset_id, dataset):
        """Dataset を差し替える（チャンネルの追加など）。チャンネルのチェック状態は名前で引き継ぐ。"""
        item = self._item(dataset_id)
        self._datasets[dataset_id] = dataset
        self.tree.blockSignals(True)
        checked = {
            item.child(i).data(0, ROLE_CHANNEL) for i in range(item.childCount())
            if item.child(i).checkState(0) == Qt.Checked
        }
        item.takeChildren()
        item.setText(0, dataset.name)
        item.setText(1, f"{len(dataset)} 点")
        self._fill_children(item, dataset, checked)
        self.tree.blockSignals(False)
        self.selection_changed.emit(self.checked_channels())

    def get(self, dataset_id):
        return self._datasets[dataset_id]

    def checked_ids(self):
        return [self._id(item) for item in self._top_items() if item.checkState(0) == Qt.Checked]

    def datasets(self):
        return [self._datasets[self._id(item)] for item in self._top_items()]

    def checked_datasets(self):
        return [self._datasets[self._id(item)] for item in self._top_items()
                if item.checkState(0) == Qt.Checked]

    def checked_channels(self):
        """チェックされた Dataset 内でチェックされたチャンネル名（順序を保った和集合）。"""
        channels = []
        for item in self._top_items():
            if item.checkState(0) != Qt.Checked:
                continue
            for i in range(item.childCount()):
                child = item.child(i)
                channel = child.data(0, ROLE_CHANNEL)
                if child.checkState(0) == Qt.Checked and channel not in channels:
                    channels.append(channel)
        return channels

    def set_checked(self, dataset_names=None, channels=None):
        """名前でチェック状態を設定する（プリセット・テスト用）。None は変更しない。"""
        self.tree.blockSignals(True)
        for item in self._top_items():
            if dataset_names is not None:
                state = Qt.Checked if item.text(0) in dataset_names else Qt.Unchecked
                item.setCheckState(0, state)
            if channels is not None:
                for i in range(item.childCount()):
                    child = item.child(i)
                    state = Qt.Checked if child.data(0, ROLE_CHANNEL) in channels else Qt.Unchecked
                    child.setCheckState(0, state)
        self.tree.blockSignals(False)
        self.selection_changed.emit(self.checked_channels())

    @staticmethod
    def _fill_children(item, dataset, checked):
        item.setToolTip(0, "\n".join(f"{k}: {v}" for k, v in dataset.meta.items() if k != "target"))
        for channel in dataset.channel_names:
            child = QtWidgets.QTreeWidgetItem([channel, dataset.unit(channel)])
            child.setData(0, ROLE_CHANNEL, channel)
            child.setFlags((child.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsEditable)
            child.setCheckState(0, Qt.Checked if channel in checked else Qt.Unchecked)
            item.addChild(child)

    def _item(self, dataset_id):
        for item in self._top_items():
            if self._id(item) == dataset_id:
                return item
        raise KeyError(f"no dataset id {dataset_id}")

    def _top_items(self):
        return [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]

    @staticmethod
    def _id(item):
        return item.data(0, ROLE_ID)

    def _on_item_changed(self, item, column):
        if item.parent() is None and column == 0:
            # 名前の変更を Dataset に反映する
            dataset_id = self._id(item)
            name = item.text(0).strip()
            if name and name != self._datasets[dataset_id].name:
                self._datasets[dataset_id] = self._datasets[dataset_id].with_name(name)
            elif not name:
                self.tree.blockSignals(True)
                item.setText(0, self._datasets[dataset_id].name)
                self.tree.blockSignals(False)
        self.selection_changed.emit(self.checked_channels())

    def _remove(self, item):
        self._datasets.pop(self._id(item), None)
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
        self.selection_changed.emit(self.checked_channels())

    def _show_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return
        if item.parent() is not None:
            item = item.parent()
        dataset = self._datasets[self._id(item)]
        menu = QtWidgets.QMenu(self)
        menu.addAction("名前を変更", lambda: self.tree.editItem(item, 0))
        menu.addAction("座標変換...", lambda: self.transform_requested.emit(self._id(item)))
        menu.addAction("npz として保存...", lambda: self.save_requested.emit(dataset))
        menu.addSeparator()
        menu.addAction("削除", lambda: self._remove(item))
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
