import sys
import ctypes

if sys.platform == "win32":
    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left",   ctypes.c_long),
            ("top",    ctypes.c_long),
            ("right",  ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    def set_cursor_clip(x: float, y: float, w: float, h: float):
        rect = _RECT(int(x), int(y), int(x + max(w, 1)), int(y + max(h, 1)))
        ctypes.windll.user32.ClipCursor(ctypes.byref(rect))

    def release_cursor_clip():
        ctypes.windll.user32.ClipCursor(None)

    def is_left_mouse_down() -> bool:
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)

elif sys.platform == "darwin":
    try:
        import Quartz

        def set_cursor_clip(x: float, y: float, w: float, h: float):
            # macOS: simulate by moving cursor to clip center each frame
            # Called every frame from dragging logic
            pass

        def release_cursor_clip():
            pass

        def is_left_mouse_down() -> bool:
            return bool(Quartz.CGEventSourceButtonState(
                Quartz.kCGEventSourceStateHIDSystemState, Quartz.kCGMouseButtonLeft
            ))

    except ImportError:
        def set_cursor_clip(x, y, w, h): pass
        def release_cursor_clip(): pass
        def is_left_mouse_down(): return False

else:
    # Linux — fall back to simulation
    def set_cursor_clip(x: float, y: float, w: float, h: float): pass
    def release_cursor_clip(): pass

    try:
        import subprocess

        def is_left_mouse_down() -> bool:
            try:
                out = subprocess.check_output(["xdotool", "getmouselocation"], timeout=0.01)
                return False  # xdotool can't easily check button state; poll via Qt instead
            except Exception:
                return False
    except Exception:
        def is_left_mouse_down(): return False
