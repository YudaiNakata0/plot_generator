"""左上: 開いた bag ファイルのツリー（ファイル → トピック → フィールド）。

トピックを展開するとフィールド一覧を取得する。フィールドにチェックを付けて
「読み込み」すると、トピックごとに Dataset を作る。
"""
import os

from core.loaders import bag

from .qt import Qt, QtWidgets, Signal

ROLE_KIND = Qt.UserRole
ROLE_PATH = Qt.UserRole + 1
ROLE_TOPIC = Qt.UserRole + 2
ROLE_TYPE = Qt.UserRole + 3
ROLE_STATE = Qt.UserRole + 4

KIND_FILE, KIND_TOPIC, KIND_FIELD = "file", "topic", "field"
# フィールド一覧の取得状態
FIELDS_NONE, FIELDS_LOADING, FIELDS_DONE = 0, 1, 2

TIME_SOURCES = [("受信時刻", "receive"), ("header.stamp", "header")]


class SourcePanel(QtWidgets.QWidget):
    # (bag パス, トピック, 読み方 "fields"/"pose"/"wrench", フィールドのリスト, time_source)
    load_requested = Signal(str, str, str, list, str)
    message = Signal(str)

    def __init__(self, jobs, parent=None):
        super().__init__(parent)
        self.jobs = jobs

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["bag", "型 / 件数"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_menu)
        self.tree.itemExpanded.connect(self._on_expanded)
        self.tree.itemDoubleClicked.connect(self._on_double_clicked)
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        self.time_source = QtWidgets.QComboBox()
        for label, value in TIME_SOURCES:
            self.time_source.addItem(label, value)

        load_button = QtWidgets.QPushButton("チェックしたフィールドを読み込む")
        load_button.clicked.connect(self.load_checked)

        clear_button = QtWidgets.QPushButton("すべて閉じる")
        clear_button.setToolTip("開いている bag をすべて閉じる（読み込んだデータセットは残る）")
        clear_button.clicked.connect(self.clear)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(QtWidgets.QLabel("時刻:"))
        bottom.addWidget(self.time_source, 1)
        bottom.addWidget(clear_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)
        layout.addLayout(bottom)
        layout.addWidget(load_button)

    # ===== bag の追加 =====

    def add_bag(self, path):
        path = os.path.abspath(path)
        for i in range(self.tree.topLevelItemCount()):
            if self.tree.topLevelItem(i).data(0, ROLE_PATH) == path:
                self.message.emit(f"すでに開いています: {path}")
                return
        item = QtWidgets.QTreeWidgetItem([os.path.basename(path), "読み込み中..."])
        item.setToolTip(0, path)
        item.setData(0, ROLE_KIND, KIND_FILE)
        item.setData(0, ROLE_PATH, path)
        self.tree.addTopLevelItem(item)
        self.jobs.submit(
            bag.list_topics, path,
            on_done=lambda topics: self._set_topics(item, topics),
            on_error=lambda msg: self._on_error(item, f"bag を開けません: {path}", msg),
        )

    def bag_count(self):
        return self.tree.topLevelItemCount()

    def clear(self):
        """開いている bag をすべて閉じる。"""
        count = self.tree.topLevelItemCount()
        if count == 0:
            return
        # tree.clear() だと項目が削除され、取得中のトピック・フィールド一覧のコールバックが
        # 削除済みの項目を触ってしまうので、取り外すだけにする
        while self.tree.topLevelItemCount():
            self.tree.takeTopLevelItem(0)
        self.message.emit(f"bag をすべて閉じました ({count} 個)")

    def _set_topics(self, file_item, topics):
        if file_item.treeWidget() is None:
            return  # 一覧の取得中に閉じられた
        file_item.setText(1, f"{len(topics)} トピック")
        path = file_item.data(0, ROLE_PATH)
        for info in topics.values():
            item = QtWidgets.QTreeWidgetItem([info.name, f"{info.msg_type} ({info.message_count})"])
            item.setToolTip(0, info.name)
            item.setData(0, ROLE_KIND, KIND_TOPIC)
            item.setData(0, ROLE_PATH, path)
            item.setData(0, ROLE_TOPIC, info.name)
            item.setData(0, ROLE_TYPE, info.msg_type)
            item.setData(0, ROLE_STATE, FIELDS_NONE)
            # 展開できるように見せ、展開時にフィールドを取得する
            item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
            file_item.addChild(item)
        file_item.setExpanded(True)
        self.message.emit(f"開きました: {path} ({len(topics)} トピック)")

    def _on_error(self, item, text, detail):
        item.setText(1, "エラー")
        self.message.emit(f"[エラー] {text}\n{detail}")

    # ===== フィールド一覧 =====

    def _on_expanded(self, item):
        if item.data(0, ROLE_KIND) == KIND_TOPIC and item.data(0, ROLE_STATE) == FIELDS_NONE:
            self._fetch_fields(item)

    def _fetch_fields(self, topic_item):
        topic_item.setData(0, ROLE_STATE, FIELDS_LOADING)
        loading = QtWidgets.QTreeWidgetItem(["読み込み中..."])
        topic_item.addChild(loading)

        def done(fields):
            topic_item.removeChild(loading)
            for f in fields:
                child = QtWidgets.QTreeWidgetItem([f.path, f.type])
                child.setData(0, ROLE_KIND, KIND_FIELD)
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)
                topic_item.addChild(child)
            topic_item.setData(0, ROLE_STATE, FIELDS_DONE)
            if not fields:
                topic_item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.DontShowIndicator)

        def failed(msg):
            topic_item.removeChild(loading)
            topic_item.setData(0, ROLE_STATE, FIELDS_NONE)
            self.message.emit(f"[エラー] フィールドを取得できません: {topic_item.data(0, ROLE_TOPIC)}\n{msg}")

        self.jobs.submit(
            bag.list_fields, topic_item.data(0, ROLE_PATH), topic_item.data(0, ROLE_TOPIC),
            on_done=done, on_error=failed,
        )

    # ===== 読み込み =====

    def _checked_fields(self, topic_item):
        return [
            topic_item.child(i).text(0)
            for i in range(topic_item.childCount())
            if topic_item.child(i).data(0, ROLE_KIND) == KIND_FIELD
            and topic_item.child(i).checkState(0) == Qt.Checked
        ]

    def _topic_items(self):
        for i in range(self.tree.topLevelItemCount()):
            file_item = self.tree.topLevelItem(i)
            for j in range(file_item.childCount()):
                yield file_item.child(j)

    def _request(self, topic_item, mode, fields=()):
        self.load_requested.emit(
            topic_item.data(0, ROLE_PATH), topic_item.data(0, ROLE_TOPIC),
            mode, list(fields), self.time_source.currentData(),
        )

    def load_checked(self):
        requested = False
        for topic_item in self._topic_items():
            fields = self._checked_fields(topic_item)
            if fields:
                self._request(topic_item, "fields", fields)
                requested = True
        if not requested:
            self.message.emit("フィールドにチェックが付いていません")

    def _quick_mode(self, topic_item):
        msg_type = topic_item.data(0, ROLE_TYPE)
        if msg_type in bag.POSE_TYPES:
            return "pose"
        if msg_type in bag.WRENCH_TYPES:
            return "wrench"
        return None

    def _on_double_clicked(self, item, column):
        # Pose / Wrench 型のトピックはダブルクリックでまとめて読み込む
        if item.data(0, ROLE_KIND) == KIND_TOPIC:
            mode = self._quick_mode(item)
            if mode:
                self._request(item, mode)

    def _show_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = QtWidgets.QMenu(self)
        if item is None:
            action = menu.addAction("すべて閉じる", self.clear)
            action.setEnabled(self.bag_count() > 0)
            menu.exec_(self.tree.viewport().mapToGlobal(pos))
            return
        kind = item.data(0, ROLE_KIND)
        if kind == KIND_FIELD:
            item = item.parent()
            kind = KIND_TOPIC
        if kind == KIND_TOPIC:
            mode = self._quick_mode(item)
            if mode == "pose":
                menu.addAction("Pose として読み込む (x, y, z, qx, qy, qz, qw)",
                               lambda: self._request(item, "pose"))
            elif mode == "wrench":
                menu.addAction("Wrench として読み込む (force_*, torque_*)",
                               lambda: self._request(item, "wrench"))
            fields = self._checked_fields(item)
            action = menu.addAction(f"チェックしたフィールドを読み込む ({len(fields)})",
                                    lambda: self._request(item, "fields", fields))
            action.setEnabled(bool(fields))
        elif kind == KIND_FILE:
            menu.addAction("閉じる", lambda: self.tree.takeTopLevelItem(
                self.tree.indexOfTopLevelItem(item)))
            menu.addAction("すべて閉じる", self.clear)
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
