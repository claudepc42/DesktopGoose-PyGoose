from dataclasses import dataclass, field
from pygoose.engine.vector2 import Vector2


@dataclass
class Rig:
    neck_lerp_percent: float = 0.0
    sit_lerp_percent: float = 0.0
    neck_tuck_lerp_percent: float = 0.0
    underbody_center: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    body_center: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    neck_center: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    neck_base: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    neck_head_point: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    head1_end_point: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    head2_end_point: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
