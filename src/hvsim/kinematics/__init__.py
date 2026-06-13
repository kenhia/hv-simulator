"""kinematics — closed-form trajectory math (accel/coast/decel, brachistochrone).

Pure functions for the trajectory solver and state evaluation, including the
moving-target intercept. Testable without running the service.
"""

from .constants import SPEED_OF_LIGHT, STANDARD_GRAVITY
from .profile import Profile, solve_profile
from .trajectory import Intercept, State, Trajectory, solve_intercept
from .vector import ZERO, Vec3

__all__ = [
    "SPEED_OF_LIGHT",
    "STANDARD_GRAVITY",
    "ZERO",
    "Intercept",
    "Profile",
    "State",
    "Trajectory",
    "Vec3",
    "solve_intercept",
    "solve_profile",
]
