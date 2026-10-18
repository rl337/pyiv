"""Use-case package for injectable clocks and datetime services.

Prefer this package over importing ``pyiv.clock`` / ``pyiv.datetime_service``
directly; those modules re-export for compatibility.

**Why this exists:** Wall-clock and calendar APIs are hard to test. Inject
``Clock`` / ``DateTimeService`` and bind synthetic doubles so tests never sleep
or depend on wall time.

Example:
    >>> from pyiv.time import SyntheticClock
    >>> clock = SyntheticClock(start_time=100.0)
    >>> clock.advance(5.0)
    >>> clock.time()
    105.0
"""

from pyiv.time.clock import Clock, RealClock, RealTimer, SyntheticClock, SyntheticTimer, Timer
from pyiv.time.datetime_service import DateTimeService, MockDateTimeService, PythonDateTimeService

__all__ = [
    "Clock",
    "RealClock",
    "SyntheticClock",
    "Timer",
    "RealTimer",
    "SyntheticTimer",
    "DateTimeService",
    "PythonDateTimeService",
    "MockDateTimeService",
]
