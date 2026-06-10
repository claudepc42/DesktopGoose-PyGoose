import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pygoose.engine.vector2 import Vector2
from pygoose.engine.math_utils import lerp, clamp, random_range
from pygoose.engine.easings import (
    cubic_ease_in_out, exponential_ease_out,
    linear, bounce_ease_out, bounce_ease_in,
)
from pygoose.engine.deck import Deck
from pygoose.engine.time_keeper import DELTA_TIME, TARGET_FRAMERATE


# --- Vector2 ---

def test_vector2_zero():
    assert Vector2.zero.x == 0.0
    assert Vector2.zero.y == 0.0

def test_vector2_add():
    a = Vector2(1.0, 2.0)
    b = Vector2(3.0, 4.0)
    r = a + b
    assert r.x == 4.0 and r.y == 6.0

def test_vector2_sub():
    r = Vector2(5.0, 3.0) - Vector2(2.0, 1.0)
    assert r.x == 3.0 and r.y == 2.0

def test_vector2_neg():
    r = -Vector2(1.0, -2.0)
    assert r.x == -1.0 and r.y == 2.0

def test_vector2_mul_scalar():
    r = Vector2(2.0, 3.0) * 2.0
    assert r.x == 4.0 and r.y == 6.0

def test_vector2_rmul_scalar():
    r = 3.0 * Vector2(1.0, 2.0)
    assert r.x == 3.0 and r.y == 6.0

def test_vector2_mul_vec():
    r = Vector2(2.0, 3.0) * Vector2(4.0, 5.0)
    assert r.x == 8.0 and r.y == 15.0

def test_vector2_div():
    r = Vector2(6.0, 4.0) / 2.0
    assert r.x == 3.0 and r.y == 2.0

def test_vector2_distance():
    d = Vector2.distance(Vector2(0.0, 0.0), Vector2(3.0, 4.0))
    assert abs(d - 5.0) < 1e-9

def test_vector2_lerp():
    r = Vector2.lerp(Vector2(0.0, 0.0), Vector2(10.0, 10.0), 0.5)
    assert abs(r.x - 5.0) < 1e-9 and abs(r.y - 5.0) < 1e-9

def test_vector2_dot():
    d = Vector2.dot(Vector2(1.0, 0.0), Vector2(0.0, 1.0))
    assert d == 0.0

def test_vector2_normalize():
    n = Vector2.normalize(Vector2(3.0, 4.0))
    assert abs(Vector2.magnitude(n) - 1.0) < 1e-9

def test_vector2_normalize_zero():
    n = Vector2.normalize(Vector2(0.0, 0.0))
    assert n.x == 0.0 and n.y == 0.0

def test_vector2_magnitude():
    m = Vector2.magnitude(Vector2(3.0, 4.0))
    assert abs(m - 5.0) < 1e-9

def test_vector2_get_from_angle_degrees():
    v = Vector2.get_from_angle_degrees(0.0)
    assert abs(v.x - 1.0) < 1e-6 and abs(v.y - 0.0) < 1e-6
    v90 = Vector2.get_from_angle_degrees(90.0)
    assert abs(v90.x - 0.0) < 1e-6 and abs(v90.y - 1.0) < 1e-6


# --- math_utils ---

def test_lerp_endpoints():
    assert lerp(0.0, 10.0, 0.0) == 0.0
    assert lerp(0.0, 10.0, 1.0) == 10.0

def test_lerp_midpoint():
    assert abs(lerp(0.0, 10.0, 0.5) - 5.0) < 1e-9

def test_clamp_below():
    assert clamp(-5.0, 0.0, 10.0) == 0.0

def test_clamp_above():
    assert clamp(15.0, 0.0, 10.0) == 10.0

def test_clamp_within():
    assert clamp(5.0, 0.0, 10.0) == 5.0

def test_random_range_bounds():
    for _ in range(1000):
        v = random_range(5.0, 10.0)
        assert 5.0 <= v < 10.0


# --- easings ---

def test_linear_endpoints():
    assert linear(0.0) == 0.0
    assert linear(1.0) == 1.0

def test_cubic_ease_in_out_endpoints():
    assert abs(cubic_ease_in_out(0.0)) < 1e-9
    assert abs(cubic_ease_in_out(1.0) - 1.0) < 1e-9

def test_cubic_ease_in_out_midpoint():
    assert abs(cubic_ease_in_out(0.5) - 0.5) < 1e-9

def test_exponential_ease_out_endpoints():
    assert abs(exponential_ease_out(0.0)) < 1e-9
    assert exponential_ease_out(1.0) == 1.0

def test_exponential_ease_out_increasing():
    vals = [exponential_ease_out(p / 10.0) for p in range(11)]
    assert all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))

def test_bounce_ease_out_endpoints():
    assert abs(bounce_ease_out(0.0)) < 1e-9
    assert abs(bounce_ease_out(1.0) - 1.0) < 1e-6

def test_bounce_ease_in_endpoints():
    assert abs(bounce_ease_in(0.0)) < 1e-9
    assert abs(bounce_ease_in(1.0) - 1.0) < 1e-6


# --- Deck ---

def test_deck_covers_all_indices():
    deck = Deck(8)
    seen = set()
    for _ in range(8):
        seen.add(deck.next())
    assert seen == set(range(8))

def test_deck_reshuffles_after_exhaust():
    deck = Deck(4)
    first_pass = [deck.next() for _ in range(4)]
    second_pass = [deck.next() for _ in range(4)]
    assert sorted(first_pass) == [0, 1, 2, 3]
    assert sorted(second_pass) == [0, 1, 2, 3]

def test_deck_length_one():
    deck = Deck(1)
    assert deck.next() == 0
    assert deck.next() == 0


# --- TimeKeeper ---

def test_delta_time_fixed():
    assert abs(DELTA_TIME - 1.0 / 120.0) < 1e-10

def test_target_framerate():
    assert TARGET_FRAMERATE == 120


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
