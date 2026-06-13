"""flightplan — compile filed flight plans into absolute-time Segment rows.

Turns ordered waypoints + layovers into a sequence of closed-form trajectory
segments so that state(t) is a lookup plus one kinematics evaluation. (Sprint 003+.)
"""
