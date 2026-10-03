#!/usr/bin/env python3
"""rosbag / npz からグラフを作る GUI アプリ。

使い方（リポジトリのトップで）:
    ./app/main.py [開くファイル (.bag / .npz) ...]
"""
import sys

from gui.qt import QtWidgets
from gui.main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.open_files(sys.argv[1:])
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
