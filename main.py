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
    """Fork so the child inherits all process context (audio session, window server)
    and detaches from the terminal via setsid. Parent exits cleanly so the shell
    regains its prompt, then osascript types 'exit' to close the Terminal window."""
    if not sys.stdout.isatty():
        return
    import os
    import subprocess

    pid = os.fork()
    if pid > 0:
        # Parent: let the shell regain its prompt, then close the Terminal window.
        subprocess.Popen(['osascript', '-e',
            'delay 0.3\ntell application "Terminal" to do script "exit" in front window'])
        os._exit(0)

    # Child: detach from the controlling terminal and silence stdio.
    os.setsid()
    devnull = open(os.devnull, 'r+')
    os.dup2(devnull.fileno(), 0)
    os.dup2(devnull.fileno(), 1)
    os.dup2(devnull.fileno(), 2)
    devnull.close()


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
