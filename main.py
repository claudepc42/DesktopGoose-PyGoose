import sys
import os

# File logger — line-buffered so every write survives a crash
_log_path = os.path.join(os.path.expanduser('~'), 'pygoose_debug.log')
_log = open(_log_path, 'w', buffering=1)
sys.stderr = _log  # capture tracebacks too

def _trace(msg):
    import datetime
    _log.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")

_trace("--- PyGoose startup ---")
_trace(f"Python {sys.version}")
_trace(f"Platform: {sys.platform}")
_trace(f"Frozen: {getattr(sys, 'frozen', False)}")
_trace(f"Executable: {sys.executable}")

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt

_trace("Qt imported OK")

from pygoose.goose.overlay import Overlay
_trace("Overlay imported OK")
from pygoose.goose.goose import Goose
_trace("Goose imported OK")
from pygoose.goose.config import load_config
_trace("config imported OK")


def _is_ax_trusted() -> bool:
    try:
        import ctypes
        appservices = ctypes.cdll.LoadLibrary(
            '/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices'
        )
        appservices.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(appservices.AXIsProcessTrusted())
    except Exception:
        return True


def _request_accessibility_macos():
    if not _is_ax_trusted():
        msg = QMessageBox()
        msg.setWindowTitle("Accessibility access needed")
        msg.setText(
            "PyGoose needs Accessibility permission to steal your mouse.\n\n"
            "Go to System Settings → Privacy & Security → Accessibility "
            "and add PyGoose to the list."
        )
        msg.exec()


def main():
    _trace("main() entered")
    app = QApplication(sys.argv)
    _trace("QApplication created")

    if sys.platform == "darwin":
        _trace("running AX check")
        _request_accessibility_macos()
        _trace("AX check done")

    _trace("loading config")
    config = load_config()
    _trace("config loaded")

    _trace("creating Goose")
    goose = Goose(config=config)
    _trace("Goose created")

    def on_tick():
        goose.tick()

    def render(painter: QPainter):
        goose.render(painter)

    _trace("creating Overlay")
    overlay = Overlay(on_tick=on_tick)
    _trace("Overlay created")

    overlay.set_render_fn(render)
    overlay.set_dirty_rect_fn(goose.dirty_rect)
    _trace("grabKeyboard")
    overlay.grabKeyboard()
    _trace("entering event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _trace(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
        raise
