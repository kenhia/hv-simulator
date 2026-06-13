"""Vec3 — a minimal immutable 3-vector (SI metres, or m/s, or m/s²).

Deliberately boring: just the operations the trajectory math needs. Shared by
later sprints (``flightplan``, ``api``). Being a ``NamedTuple`` it is immutable,
hashable, and unpacks as ``x, y, z = v``.
"""

from __future__ import annotations

import math
from typing import NamedTuple


class Vec3(NamedTuple):
    x: float
    y: float
    z: float

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def norm(self) -> float:
        return math.sqrt(self.dot(self))

    def unit(self) -> Vec3:
        n = self.norm()
        if n == 0.0:
            raise ValueError("cannot take the unit vector of a zero vector")
        return Vec3(self.x / n, self.y / n, self.z / n)


ZERO = Vec3(0.0, 0.0, 0.0)
