import sys
import ctypes
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020


class Overlay(QWidget):
    def __init__(self, on_tick=None):
        super().__init__()
        self._on_tick = on_tick
        self._setup_window()
        self._apply_click_through()
        self._start_loop()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.show()

    def _apply_click_through(self):
        if sys.platform == "win32":
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            )

    def _start_loop(self):
        self._timer = QTimer()
        self._timer.setInterval(8)  # ~120fps, lets Qt event loop pace itself
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        if self._on_tick:
            self._on_tick()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint(painter)
        painter.end()

    def _paint(self, painter: QPainter):
        pass  # subclasses or game object override via set_render_fn

    def set_render_fn(self, fn):
        self._paint = fn
