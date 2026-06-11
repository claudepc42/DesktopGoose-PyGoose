from math import atan2, degrees, sin, pi
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QPointF, QRectF

from pygoose.engine.vector2 import Vector2
from pygoose.engine.math_utils import lerp, clamp
from pygoose.engine.rig import Rig

FOOT_MARK_LIFETIME = 8.5
FOOT_MARK_SHRINK_TIME = 1.0

UP = Vector2(0.0, -1.0)

COLOR_WHITE = QColor("white")
COLOR_LIGHT_GRAY = QColor("lightgray")
COLOR_ORANGE = QColor("orange")
COLOR_BLACK = QColor("black")
COLOR_SADDLE_BROWN = QColor(0x8B, 0x45, 0x13)
COLOR_YELLOW = QColor(0xFF, 0xE0, 0x00)


def update_rig(position: Vector2, direction: float, rig: Rig):
    fwd = Vector2.get_from_angle_degrees(direction)
    s = rig.sit_lerp_percent

    rig.underbody_center = position + UP * lerp(9.0, 1.0, s)
    rig.body_center      = position + UP * lerp(14.0, 4.0, s)

    tuck = rig.neck_tuck_lerp_percent
    neck_height  = int(lerp(lerp(20.0, 10.0, rig.neck_lerp_percent), 6.0,  tuck))
    neck_forward = int(lerp(lerp(3.0,  16.0, rig.neck_lerp_percent), 2.0,  tuck))

    rig.neck_center = position + UP * (14 + neck_height)
    rig.neck_base = rig.body_center + fwd * 15.0
    rig.neck_head_point = rig.neck_base + fwd * neck_forward + UP * neck_height

    rig.head1_end_point = rig.neck_head_point + fwd * 3.0 - UP * 1.0
    rig.head2_end_point = rig.head1_end_point + fwd * 5.0


def _pt(v: Vector2) -> QPointF:
    return QPointF(v.x, v.y)


def _set_pen(painter: QPainter, color: QColor, width: int):
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)


def render_foot_marks(painter: QPainter, foot_marks: list, current_time: float):
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(COLOR_SADDLE_BROWN))
    for mark in foot_marks:
        if mark.time == 0.0:
            continue
        shrink_start = mark.time + FOOT_MARK_LIFETIME
        p = clamp((current_time - shrink_start) / FOOT_MARK_SHRINK_TIME, 0.0, 1.0)
        radius = lerp(3.0, 0.0, p)
        if radius > 0:
            painter.drawEllipse(_pt(mark.position), radius, radius)


def render_goose(painter: QPainter, rig: Rig, position: Vector2, direction: float,
                 l_foot_pos: Vector2, r_foot_pos: Vector2,
                 config=None):
    fwd = Vector2.get_from_angle_degrees(direction)
    right = Vector2.get_from_angle_degrees(direction + 90.0)

    body_color = COLOR_WHITE
    outline_color = COLOR_LIGHT_GRAY
    beak_color = COLOR_ORANGE

    if config and config.use_custom_colors:
        body_color = QColor(config.goose_color_body)
        outline_color = QColor(config.goose_color_underbody)
        beak_color = QColor(config.goose_color_beak)

    # 1. Shadow — hatched dark gray ellipse
    painter.setPen(Qt.PenStyle.NoPen)
    shadow_brush = QBrush(QColor(80, 80, 80, 80), Qt.BrushStyle.Dense4Pattern)
    painter.setBrush(shadow_brush)
    painter.drawEllipse(QPointF(position.x, position.y), 20.0, 15.0)

    # 2. Feet
    painter.setBrush(QBrush(beak_color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(_pt(l_foot_pos), 4.0, 4.0)
    painter.drawEllipse(_pt(r_foot_pos), 4.0, 4.0)

    # 3. Outline layer (light gray, drawn first so white overwrites)
    _set_pen(painter, outline_color, 15)
    painter.drawLine(_pt(rig.underbody_center + fwd * 7), _pt(rig.underbody_center - fwd * 7))

    _set_pen(painter, outline_color, 24)
    painter.drawLine(_pt(rig.body_center + fwd * 11), _pt(rig.body_center - fwd * 11))

    _set_pen(painter, outline_color, 15)
    painter.drawLine(_pt(rig.neck_base), _pt(rig.neck_head_point))

    _set_pen(painter, outline_color, 17)
    painter.drawLine(_pt(rig.neck_head_point), _pt(rig.head1_end_point))

    _set_pen(painter, outline_color, 12)
    painter.drawLine(_pt(rig.head1_end_point), _pt(rig.head2_end_point))

    # 4. White fill layer
    _set_pen(painter, body_color, 22)
    painter.drawLine(_pt(rig.body_center + fwd * 11), _pt(rig.body_center - fwd * 11))

    _set_pen(painter, body_color, 13)
    painter.drawLine(_pt(rig.neck_base), _pt(rig.neck_head_point))

    _set_pen(painter, body_color, 15)
    painter.drawLine(_pt(rig.neck_head_point), _pt(rig.head1_end_point))

    _set_pen(painter, body_color, 10)
    painter.drawLine(_pt(rig.head1_end_point), _pt(rig.head2_end_point))

    # 5. Beak
    _set_pen(painter, beak_color, 11)
    painter.drawLine(_pt(rig.head2_end_point), _pt(rig.head2_end_point + fwd * 5))

    # 6. Eyes (hidden while sleeping, one may peek during fake sleep)
    b = Vector2(1.3, 0.4)
    left_eye  = rig.neck_head_point + UP * 3 - right * b.x * 3 + fwd * 5
    right_eye = rig.neck_head_point + UP * 3 + right * b.x * 3 + fwd * 5
    painter.setBrush(QBrush(COLOR_BLACK))
    painter.setPen(Qt.PenStyle.NoPen)
    if not rig.is_sleeping or rig.peek_eye == 3:
        painter.drawEllipse(_pt(left_eye), 2.0, 2.0)
        painter.drawEllipse(_pt(right_eye), 2.0, 2.0)
    elif rig.peek_eye == 1:
        painter.drawEllipse(_pt(left_eye), 2.0, 2.0)
    elif rig.peek_eye == 2:
        painter.drawEllipse(_pt(right_eye), 2.0, 2.0)

    # 7. Sleep bubbles
    if rig.show_sleep_bubbles:
        _render_sleep_bubbles(painter, rig)

    # 8. Exclamation mark
    if rig.show_exclamation:
        _render_exclamation(painter, rig)


def _render_sleep_bubbles(painter: QPainter, rig: Rig):
    base = rig.neck_head_point + UP * 10.0
    # 3 bubbles with staggered phases, each cycling over 3 seconds
    configs = [
        {"offset": 0.0,  "x_drift":  6.0, "max_r": 3.5},
        {"offset": 1.0,  "x_drift": 11.0, "max_r": 5.0},
        {"offset": 2.0,  "x_drift": 15.0, "max_r": 6.5},
    ]
    cycle = 3.0
    rise  = 28.0
    for cfg in configs:
        p = ((rig.sleep_phase + cfg["offset"]) % cycle) / cycle  # 0→1
        alpha = int(clamp(lerp(220, 0, max(0.0, (p - 0.5) * 2.0)), 0, 255))
        if alpha == 0:
            continue
        r   = lerp(1.5, cfg["max_r"], p)
        pos = Vector2(base.x + cfg["x_drift"], base.y - p * rise)
        color = QColor(255, 255, 255, alpha)
        outline = QColor(160, 200, 255, alpha)
        pen = QPen(outline, 1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(_pt(pos), r, r)


def _render_exclamation(painter: QPainter, rig: Rig):
    base = rig.neck_head_point + UP * 22.0
    outline_pen = QPen(COLOR_BLACK, 1.5)
    outline_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(outline_pen)
    painter.setBrush(QBrush(COLOR_YELLOW))
    # Vertical bar: tall thin rounded rect
    bar = QRectF(base.x - 3.5, base.y - 14.0, 7.0, 10.0)
    painter.drawRoundedRect(bar, 2.0, 2.0)
    # Dot below
    painter.drawEllipse(QPointF(base.x, base.y), 3.5, 3.5)
