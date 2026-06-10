from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QMetaObject, Q_ARG
from PyQt6.QtGui import QCloseEvent


class MovableWindow(QWidget):
    closing = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

    def move_threadsafe(self, x: int, y: int):
        QMetaObject.invokeMethod(
            self, "_do_move",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, x),
            Q_ARG(int, y),
        )

    @pyqtSlot(int, int)
    def _do_move(self, x: int, y: int):
        self.move(x, y)
        self.raise_()

    def closeEvent(self, event: QCloseEvent):
        self.closing.emit()
        super().closeEvent(event)
