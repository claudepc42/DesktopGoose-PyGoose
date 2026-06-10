import time as _time

TARGET_FRAMERATE = 120
DELTA_TIME = 1.0 / 120.0  # 0.008333334 — fixed, not measured


class TimeKeeper:
    def __init__(self):
        self._start = _time.perf_counter()
        self._frame_deadline = self._start + DELTA_TIME
        self.time: float = 0.0
        self.delta_time: float = DELTA_TIME

    def tick(self):
        self.time = _time.perf_counter() - self._start

    def sleep_remainder(self):
        now = _time.perf_counter()
        sleep_dur = self._frame_deadline - now
        if sleep_dur > 0:
            _time.sleep(sleep_dur)
        self._frame_deadline += DELTA_TIME
