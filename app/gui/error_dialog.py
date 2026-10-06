"""誤差計算のダイアログ（データセットの右クリック →「誤差の計算...」）。

目標値との誤差を派生チャンネルとして追加する。
    各軸の誤差      : v - 目標値（calculate_error.py -s）
    位置誤差 r      : 3 チャンネルの目標位置とのユークリッド距離（calculate_error_rad.py）
    姿勢誤差 θ      : roll, pitch, yaw → クォータニオン → 目標姿勢との差の回転角（record_orientation.py）
"""
from core.processing import error

from .qt import QtGui, QtWidgets

# (表示名, 種類, 既定の入力チャンネル, 既定の出力名)
KINDS = [
    ("位置誤差 r（x, y, z）", "position", ("x", "y", "z"), "r"),
    ("姿勢誤差 θ（roll, pitch, yaw）", "orientation", ("roll", "pitch", "yaw"), "theta"),
    ("各軸の誤差（v − 目標値）", "axis", ("x", "y", "z"), error.AXIS_SUFFIX),
]
TARGET_MODES = [
    ("ファイルの目標値", "file"),
    ("指定する", "manual"),
]


class ErrorDialog(QtWidgets.QDialog):
    def __init__(self, dataset, checked_count=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"誤差の計算: {dataset.name}")
        self.dataset = dataset

        explanation = QtWidgets.QLabel(
            "目標値との誤差を新しいチャンネルとして追加します（元のチャンネルは残ります）。\n"
            "追加したチャンネルの目標値は 0 になるので、統計の RMSE が RMS 誤差になります。\n"
            "姿勢誤差 θ は 2·arccos(|dq.w|)（0〜π）で、q と −q を同じ姿勢として扱います。"
        )
        explanation.setWordWrap(True)

        self.kind = QtWidgets.QComboBox()
        for label, value, _, _ in KINDS:
            self.kind.addItem(label, value)

        self.channel_combos = []
        channel_row = QtWidgets.QHBoxLayout()
        for _ in range(3):
            combo = QtWidgets.QComboBox()
            combo.addItems(dataset.channel_names)
            combo.currentTextChanged.connect(self._update_targets)
            channel_row.addWidget(combo, 1)
            self.channel_combos.append(combo)

        self.target_mode = QtWidgets.QComboBox()
        for label, value in TARGET_MODES:
            self.target_mode.addItem(label, value)
        self.target_mode.currentIndexChanged.connect(self._update_targets)

        self.target_edits = []
        target_row = QtWidgets.QHBoxLayout()
        for _ in range(3):
            edit = QtWidgets.QLineEdit()
            edit.setValidator(QtGui.QDoubleValidator())
            target_row.addWidget(edit, 1)
            self.target_edits.append(edit)

        self.output = QtWidgets.QLineEdit()
        self.output_label = QtWidgets.QLabel()

        self.apply_all = QtWidgets.QCheckBox(f"チェックしたデータセットすべてに適用 ({checked_count} 件)")
        self.apply_all.setEnabled(checked_count > 1)
        self.apply_all.setToolTip("目標値を「ファイルの目標値」にすると、データセットごとの目標値が使われる")

        form = QtWidgets.QFormLayout()
        form.addRow("種類", self.kind)
        form.addRow("入力チャンネル", channel_row)
        form.addRow("目標値", self.target_mode)
        form.addRow("", target_row)
        form.addRow(self.output_label, self.output)
        form.addRow("", self.apply_all)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(explanation)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.kind.currentIndexChanged.connect(self._on_kind_changed)
        self._on_kind_changed()

    def values(self):
        """入力値。検証は validate() で行う。"""
        mode = self.target_mode.currentData()
        targets = None
        if mode == "manual":
            targets = [float(edit.text()) for edit in self.target_edits]
        return dict(
            kind=self.kind.currentData(),
            channels=tuple(combo.currentText() for combo in self.channel_combos),
            target_mode=mode,
            targets=targets,
            output=self.output.text().strip(),
            apply_all=self.apply_all.isChecked(),
        )

    def validate(self):
        """問題があればメッセージを返す。無ければ None。"""
        try:
            values = self.values()
        except ValueError:
            return "目標値を正しく入力してください"
        if len(set(values["channels"])) != 3:
            return "入力チャンネルは 3 つとも別のものを選んでください"
        if not values["output"]:
            return "出力名を入力してください"
        if values["kind"] != "axis" and values["output"] in values["channels"]:
            return "出力チャンネル名が入力チャンネルと同じです"
        if values["target_mode"] == "file" and not values["apply_all"]:
            try:
                error.resolve_targets(self.dataset, values["channels"])
            except ValueError as e:
                return f"{e}\n目標値を「指定する」にしてください"
        return None

    def accept(self):
        message = self.validate()
        if message:
            QtWidgets.QMessageBox.warning(self, "誤差の計算", message)
            return
        super().accept()

    def _on_kind_changed(self):
        _, kind, defaults, output = KINDS[self.kind.currentIndex()]
        names = self.dataset.channel_names
        for combo, default in zip(self.channel_combos, defaults):
            if default in names:
                combo.setCurrentText(default)
        self.output.setText(output)
        self.output_label.setText("接尾辞" if kind == "axis" else "出力チャンネル名")
        self.output.setToolTip(
            "出力チャンネル名 = 入力チャンネル名 + 接尾辞（例: x → x_err）。同じ名前があれば上書き"
            if kind == "axis" else "同じ名前のチャンネルがあれば上書き")
        self._update_targets()

    def _update_targets(self):
        manual = self.target_mode.currentData() == "manual"
        for combo, edit in zip(self.channel_combos, self.target_edits):
            edit.setEnabled(manual)
            if not manual:
                value = self.dataset.target_for(combo.currentText())
                edit.setText("" if value is None else f"{value:.6g}")
            edit.setPlaceholderText("目標値なし" if not manual else "")
