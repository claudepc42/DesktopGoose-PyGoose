import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt

from pygoose.goose.overlay import Overlay
from pygoose.goose.goose import Goose
from pygoose.goose.config import load_config


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


def _detach_from_terminal():
    """If launched from a terminal (e.g. Finder double-click), re-launch detached so
    closing the terminal window doesn't kill the goose. Prints a message and exits
    the terminal-attached process; Terminal closes itself when it exits cleanly."""
    if not sys.stdout.isatty():
        return
    import subprocess
    print("\033[1;31m▶ PyGoose is loading — this window will close shortly.\033[0m", flush=True)
    print("\033[1;31m  To quit once running: hold Escape for 5 seconds.\033[0m", flush=True)
    subprocess.Popen(
        [sys.executable],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sys.exit(0)


def main():
    if sys.platform == "darwin":
        _detach_from_terminal()

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
