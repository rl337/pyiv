"""Compatibility re-exports for ``pyiv.time`` clock types."""

from pyiv.time.clock import Clock, RealClock, RealTimer, SyntheticClock, SyntheticTimer, Timer

__all__ = [
    "Clock",
    "RealClock",
    "SyntheticClock",
    "Timer",
    "RealTimer",
    "SyntheticTimer",
]
