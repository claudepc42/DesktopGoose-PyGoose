from __future__ import annotations
import math


class Vector2:
    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __mul__(self, other) -> Vector2:
        if isinstance(other, Vector2):
            return Vector2(self.x * other.x, self.y * other.y)
        return Vector2(self.x * other, self.y * other)

    def __rmul__(self, other) -> Vector2:
        return Vector2(self.x * other, self.y * other)

    def __truediv__(self, scalar: float) -> Vector2:
        return Vector2(self.x / scalar, self.y / scalar)

    def __repr__(self) -> str:
        return f"Vector2({self.x}, {self.y})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vector2):
            return False
        return self.x == other.x and self.y == other.y

    @staticmethod
    def get_from_angle_degrees(angle: float) -> Vector2:
        rad = angle * 0.0174532924
        return Vector2(math.cos(rad), math.sin(rad))

    @staticmethod
    def distance(a: Vector2, b: Vector2) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def lerp(a: Vector2, b: Vector2, p: float) -> Vector2:
        return Vector2(
            a.x * (1.0 - p) + b.x * p,
            a.y * (1.0 - p) + b.y * p,
        )

    @staticmethod
    def dot(a: Vector2, b: Vector2) -> float:
        return a.x * b.x + a.y * b.y

    @staticmethod
    def normalize(a: Vector2) -> Vector2:
        if a.x == 0.0 and a.y == 0.0:
            return Vector2(0.0, 0.0)
        mag = math.sqrt(a.x * a.x + a.y * a.y)
        return Vector2(a.x / mag, a.y / mag)

    @staticmethod
    def magnitude(a: Vector2) -> float:
        return math.sqrt(a.x * a.x + a.y * a.y)


Vector2.zero = Vector2(0.0, 0.0)
