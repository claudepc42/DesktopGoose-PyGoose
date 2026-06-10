import random as _random

DEG2RAD = 0.0174532924
RAD2DEG = 57.2957764

_rng = _random.Random()


def random_range(min_val: float, max_val: float) -> float:
    return min_val + _rng.random() * (max_val - min_val)


def lerp(a: float, b: float, p: float) -> float:
    return a * (1.0 - p) + b * p


def clamp(a: float, min_val: float, max_val: float) -> float:
    return min(max(a, min_val), max_val)


def get_rng() -> _random.Random:
    return _rng
