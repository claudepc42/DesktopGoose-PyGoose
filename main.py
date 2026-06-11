import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt

from pygoose.goose.overlay import Overlay
from pygoose.goose.goose import Goose
from pygoose.goose.config import load_config


def _request_accessibility_macos():
    try:
        import Quartz
    except ImportError:
        msg = QMessageBox()
        msg.setWindowTitle("Missing dependency")
        msg.setText(
            "PyGoose needs pyobjc-framework-Quartz for full mouse interaction on macOS.\n\n"
            "Install it with:\n\n"
            "    pip install pyobjc-framework-Quartz\n\n"
            "The goose will still run without it, but won't be able to steal your mouse."
        )
        msg.exec()
        return

    if not Quartz.AXIsProcessTrusted():
        msg = QMessageBox()
        msg.setWindowTitle("Accessibility access needed")
        msg.setText(
            "PyGoose needs Accessibility permission to steal your mouse.\n\n"
            "Go to System Settings → Privacy & Security → Accessibility "
            "and add Terminal (or PyGoose) to the list."
        )
        msg.exec()


def main():
    app = QApplication(sys.argv)

    if sys.platform == "darwin":
        _request_accessibility_macos()

    config = load_config()
    goose = Goose(config=config)

    def on_tick():
        goose.tick()

    def render(painter: QPainter):
        goose.render(painter)

    overlay = Overlay(on_tick=on_tick)
    overlay.set_render_fn(render)
    overlay.set_dirty_rect_fn(goose.dirty_rect)
    overlay.grabKeyboard()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
