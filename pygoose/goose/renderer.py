from math import atan2, degrees
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

    # 6. Eyes
    b = Vector2(1.3, 0.4)
    left_eye = rig.neck_head_point + UP * 3 - right * b.x * 3 + fwd * 5
    right_eye = rig.neck_head_point + UP * 3 + right * b.x * 3 + fwd * 5
    painter.setBrush(QBrush(COLOR_BLACK))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(_pt(left_eye), 2.0, 2.0)
    painter.drawEllipse(_pt(right_eye), 2.0, 2.0)
