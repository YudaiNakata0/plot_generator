"""Qt の読み込みはここに集約する（Qt6 へ移行するときはここを差し替える）。

matplotlib 3.5.1 は QT_API が未指定だと PyQt6 / PySide6 を優先して探す。
~/.local に入っている PySide6 6.11 とは組み合わせると動かないので、PyQt5 を明示する。
"""
import os

os.environ.setdefault("QT_API", "pyqt5")

from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: E402
from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtCore import pyqtSignal as Signal  # noqa: E402
from PyQt5.QtCore import pyqtSlot as Slot  # noqa: E402
from matplotlib.backends.backend_qtagg import (  # noqa: E402
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)

__all__ = [
    "QtCore", "QtGui", "QtWidgets", "Qt", "Signal", "Slot",
    "FigureCanvasQTAgg", "NavigationToolbar2QT",
]
