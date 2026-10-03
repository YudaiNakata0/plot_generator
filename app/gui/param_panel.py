"""右: グラフ種類の選択と、Param 定義から自動生成する設定フォーム。

入力欄は文字列のまま保持し、型変換・デフォルト補完は PlotType.resolve_params に任せる。
空欄は「未指定 (None)」で、0 とは区別される。
"""
import json

from plots import REGISTRY

from .qt import QtGui, QtWidgets, Signal


class ParamPanel(QtWidgets.QWidget):
    draw_requested = Signal(bool)  # new_tab
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = []
        self._widgets = {}
        # per_channel の入力値 {param key: {channel: 文字列}}（チャンネルが変わっても保持する）
        self._per_channel_values = {}

        self.type_combo = QtWidgets.QComboBox()
        for name, cls in REGISTRY.items():
            self.type_combo.addItem(name)
            self.type_combo.setItemData(self.type_combo.count() - 1, cls.description, 3)  # ToolTipRole
        self.type_combo.currentTextChanged.connect(self._rebuild)

        self.description = QtWidgets.QLabel()
        self.description.setWordWrap(True)

        self.form_host = QtWidgets.QWidget()
        self.form = QtWidgets.QFormLayout(self.form_host)
        self.form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        # 入力欄が多いときは潰さずにスクロールさせる
        self.form.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.form_host)

        draw_button = QtWidgets.QPushButton("描画")
        draw_button.setDefault(True)
        draw_button.clicked.connect(lambda: self.draw_requested.emit(False))
        new_tab_button = QtWidgets.QPushButton("新しいタブに描画")
        new_tab_button.clicked.connect(lambda: self.draw_requested.emit(True))
        reset_button = QtWidgets.QPushButton("初期値に戻す")
        reset_button.clicked.connect(self.reset)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(draw_button)
        buttons.addWidget(new_tab_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel("グラフの種類"))
        layout.addWidget(self.type_combo)
        layout.addWidget(self.description)
        layout.addWidget(scroll, 1)
        layout.addWidget(reset_button)
        layout.addLayout(buttons)

        self._rebuild()

    # ===== 公開 API =====

    @property
    def plot_type(self):
        return REGISTRY[self.type_combo.currentText()]

    def set_channels(self, channels):
        """描画対象のチャンネルが変わったら、チャンネルごとの入力欄を作り直す。"""
        if channels == self._channels:
            return
        self._store_per_channel()
        self._channels = list(channels)
        self._rebuild(keep_values=True)

    def values(self):
        """入力値を {key: 文字列 / bool / {channel: 文字列}} で返す。"""
        self._store_per_channel()
        values = self._plain_values()
        for param in self.plot_type.params:
            if param.per_channel:
                values[param.key] = {
                    ch: text for ch, text in self._per_channel_values.get(param.key, {}).items()
                    if ch in self._channels and text != ""
                }
        return values

    def set_values(self, values):
        for param in self.plot_type.params:
            if param.key not in values:
                continue
            value = values[param.key]
            if param.per_channel:
                self._per_channel_values[param.key] = {
                    ch: "" if v is None else str(v) for ch, v in dict(value or {}).items()
                }
            else:
                self._set_widget(self._widgets[param.key], value)
        self._rebuild(keep_values=True)

    def reset(self):
        self._per_channel_values = {}
        self._rebuild()

    def save_preset(self, path):
        preset = {"plot_type": self.plot_type.name, "params": self.values()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)

    def load_preset(self, path):
        with open(path, encoding="utf-8") as f:
            preset = json.load(f)
        name = preset.get("plot_type")
        if name not in REGISTRY:
            raise KeyError(f"unknown plot type: {name}")
        self.type_combo.setCurrentText(name)
        self.reset()
        self.set_values(preset.get("params", {}))

    # ===== フォーム =====

    def _plain_values(self):
        """per_channel 以外の入力欄の値（per_channel の値は _per_channel_values に別で保持）。"""
        values = {}
        for param in self.plot_type.params:
            widget = self._widgets.get(param.key)
            if widget is None or param.per_channel:
                continue
            if isinstance(widget, QtWidgets.QCheckBox):
                values[param.key] = widget.isChecked()
            elif isinstance(widget, QtWidgets.QComboBox):
                values[param.key] = widget.currentText()
            else:
                values[param.key] = widget.text().strip()
        return values

    def _rebuild(self, *_, keep_values=False):
        old = self._plain_values() if keep_values else {}
        while self.form.rowCount():
            self.form.removeRow(0)
        self._widgets = {}

        cls = self.plot_type
        self.description.setText(cls.description)
        for param in cls.params:
            label = param.label or param.key
            if param.unit:
                label += f" [{param.unit}]"
            if param.per_channel:
                widget = self._make_per_channel(param, label)
            else:
                widget = self._make_widget(param)
                if param.key in old:
                    self._set_widget(widget, old[param.key])
            if param.help:
                widget.setToolTip(param.help)
            self._widgets[param.key] = widget
            if param.per_channel:
                self.form.addRow(widget)
            else:
                self.form.addRow(label, widget)

    @staticmethod
    def _make_widget(param):
        if param.type is bool:
            widget = QtWidgets.QCheckBox()
            widget.setChecked(bool(param.default))
        elif param.choices:
            widget = QtWidgets.QComboBox()
            widget.addItems([str(c) for c in param.choices])
            if param.default is not None:
                widget.setCurrentText(str(param.default))
        else:
            widget = QtWidgets.QLineEdit()
            if param.default is not None:
                widget.setText(str(param.default))
            widget.setPlaceholderText("未指定")
            if param.type is float:
                validator = QtGui.QDoubleValidator()
                validator.setNotation(QtGui.QDoubleValidator.ScientificNotation)
                widget.setValidator(validator)
            elif param.type is int:
                widget.setValidator(QtGui.QIntValidator())
        return widget

    def _make_per_channel(self, param, label):
        box = QtWidgets.QGroupBox(label)
        layout = QtWidgets.QFormLayout(box)
        layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        layout.setVerticalSpacing(4)
        stored = self._per_channel_values.get(param.key, {})
        box.edits = {}
        if not self._channels:
            layout.addRow(QtWidgets.QLabel("（チャンネル未選択）"))
        for channel in self._channels:
            edit = QtWidgets.QLineEdit(stored.get(channel, ""))
            edit.setPlaceholderText("未指定")
            if param.type is float:
                edit.setValidator(QtGui.QDoubleValidator())
            layout.addRow(channel, edit)
            box.edits[channel] = edit
        return box

    @staticmethod
    def _set_widget(widget, value):
        if isinstance(widget, QtWidgets.QCheckBox):
            if isinstance(value, str):
                value = value.lower() in ("1", "true", "yes", "on")
            widget.setChecked(bool(value))
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.setCurrentText(str(value))
        else:
            widget.setText("" if value is None else str(value))

    def _store_per_channel(self):
        for param in self.plot_type.params:
            if not param.per_channel or param.key not in self._widgets:
                continue
            stored = self._per_channel_values.setdefault(param.key, {})
            for channel, edit in self._widgets[param.key].edits.items():
                stored[channel] = edit.text().strip()
