"""座標変換のダイアログ（データセットの右クリック →「座標変換...」）。

p' = R_軸(角度) · (p - 原点) を計算し、接尾辞付きのチャンネル（x', y', z' など）を追加する。
"""
import math

from core.processing import transform

from .qt import QtGui, QtWidgets

ORIGIN_MODES = [
    ("目標位置（ファイルの目標値）", "target"),
    ("指定する", "manual"),
    ("移動しない", "none"),
]
AXIS_CHOICES = [("回転しない", None), ("x 軸", "x"), ("y 軸", "y"), ("z 軸", "z")]


class TransformDialog(QtWidgets.QDialog):
    def __init__(self, dataset, checked_count=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"座標変換: {dataset.name}")
        self.dataset = dataset

        explanation = QtWidgets.QLabel(
            "p' = R(角度) · (p − 原点) を計算し、接尾辞を付けたチャンネルとして追加します（元のチャンネルは残ります）。\n"
            "傾いた壁面（scripts/draw_trajectory.py の -p 角度）と同じ変換は、"
            "原点 = 目標位置、回転軸 = y 軸、角度 = pitch [rad] です。"
        )
        explanation.setWordWrap(True)

        # 入力チャンネル
        self.channel_combos = []
        channel_row = QtWidgets.QHBoxLayout()
        names = dataset.channel_names
        for i, default in enumerate(transform.AXES):
            combo = QtWidgets.QComboBox()
            combo.addItems(names)
            if default in names:
                combo.setCurrentText(default)
            elif i < len(names):
                combo.setCurrentIndex(i)
            combo.currentTextChanged.connect(self._update_target_label)
            channel_row.addWidget(QtWidgets.QLabel(default))
            channel_row.addWidget(combo, 1)
            self.channel_combos.append(combo)

        # 原点
        self.origin_mode = QtWidgets.QComboBox()
        for label, value in ORIGIN_MODES:
            self.origin_mode.addItem(label, value)
        self.origin_mode.currentIndexChanged.connect(self._update_origin_enabled)
        self.target_label = QtWidgets.QLabel()
        self.origin_edits = []
        origin_row = QtWidgets.QHBoxLayout()
        for axis in transform.AXES:
            edit = QtWidgets.QLineEdit("0")
            edit.setValidator(QtGui.QDoubleValidator())
            origin_row.addWidget(QtWidgets.QLabel(axis))
            origin_row.addWidget(edit, 1)
            self.origin_edits.append(edit)

        # 回転
        self.axis = QtWidgets.QComboBox()
        for label, value in AXIS_CHOICES:
            self.axis.addItem(label, value)
        self.axis.setCurrentIndex(2)  # y 軸（傾いた壁面の既定）
        self.angle = QtWidgets.QLineEdit("0")
        self.angle.setValidator(QtGui.QDoubleValidator())
        self.angle_deg = QtWidgets.QLabel()
        self.angle.textChanged.connect(self._update_angle_deg)
        angle_row = QtWidgets.QHBoxLayout()
        angle_row.addWidget(self.angle, 1)
        angle_row.addWidget(self.angle_deg)

        self.suffix = QtWidgets.QLineEdit("'")
        self.suffix.setToolTip("出力チャンネル名 = 入力チャンネル名 + 接尾辞（例: y → y'）。同じ名前があれば上書き")

        self.apply_all = QtWidgets.QCheckBox(f"チェックしたデータセットすべてに適用 ({checked_count} 件)")
        self.apply_all.setEnabled(checked_count > 1)
        self.apply_all.setToolTip("原点を「目標位置」にすると、データセットごとの目標位置が使われる")

        form = QtWidgets.QFormLayout()
        form.addRow("入力チャンネル", channel_row)
        form.addRow("原点", self.origin_mode)
        form.addRow("", self.target_label)
        form.addRow("原点の座標", origin_row)
        form.addRow("回転軸", self.axis)
        form.addRow("角度 [rad]", angle_row)
        form.addRow("接尾辞", self.suffix)
        form.addRow("", self.apply_all)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(explanation)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._update_target_label()
        self._update_origin_enabled()
        self._update_angle_deg()

    def values(self):
        """入力値。検証は validate() で行う。"""
        origin = None
        mode = self.origin_mode.currentData()
        if mode == "manual":
            origin = tuple(float(edit.text() or 0) for edit in self.origin_edits)
        return dict(
            channels=tuple(combo.currentText() for combo in self.channel_combos),
            origin_mode=mode,
            origin=origin,
            axis=self.axis.currentData(),
            angle=float(self.angle.text() or 0),
            suffix=self.suffix.text().strip(),
            apply_all=self.apply_all.isChecked(),
        )

    def validate(self):
        """問題があればメッセージを返す。無ければ None。"""
        try:
            values = self.values()
        except ValueError:
            return "数値を正しく入力してください"
        if len(set(values["channels"])) != 3:
            return "入力チャンネルは 3 つとも別のものを選んでください"
        if not values["suffix"]:
            return "接尾辞を入力してください（空だと元のチャンネルを上書きしてしまいます）"
        if values["origin_mode"] == "target" and not values["apply_all"] \
                and transform.target_origin(self.dataset, values["channels"]) is None:
            return "このデータセットには 3 チャンネル分の目標値がありません。原点を「指定する」にしてください"
        return None

    def accept(self):
        message = self.validate()
        if message:
            QtWidgets.QMessageBox.warning(self, "座標変換", message)
            return
        super().accept()

    def _update_target_label(self):
        channels = [combo.currentText() for combo in self.channel_combos]
        origin = transform.target_origin(self.dataset, channels)
        if origin is None:
            self.target_label.setText("（このデータセットには目標値がありません）")
        else:
            self.target_label.setText("目標位置: (" + ", ".join(f"{v:.6g}" for v in origin) + ")")

    def _update_origin_enabled(self):
        manual = self.origin_mode.currentData() == "manual"
        for edit in self.origin_edits:
            edit.setEnabled(manual)

    def _update_angle_deg(self):
        try:
            self.angle_deg.setText(f"= {math.degrees(float(self.angle.text() or 0)):.4g}°")
        except ValueError:
            self.angle_deg.setText("")
