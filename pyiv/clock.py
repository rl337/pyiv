"""Clock abstraction for dependency injection.

This module provides abstract interfaces and implementations for time-related
operations, enabling dependency injection of time functionality for easier
testing and flexible time management.

Architecture:
    - Clock: Abstract base class defining the time interface
    - RealClock: Production implementation using Python's time module
    - SyntheticClock: Test implementation with manual time control
    - Timer: Abstract interface for scheduled callbacks
    - RealTimer/SyntheticTimer: Concrete timer implementations

Usage:
    For production code, use RealClock which provides actual system time.
    For testing, use SyntheticClock which allows manual time advancement.

    Example:
        >>> from pyiv.clock import RealClock, SyntheticClock
        >>> # Production
        >>> clock = RealClock()
        >>> current = clock.time()
        >>> clock.sleep(1.0)
        >>> # Testing
        >>> test_clock = SyntheticClock(start_time=100.0)
        >>> test_clock.advance(5.0)  # Advance time manually
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional


class Clock(ABC):
    """Abstract clock interface for time operations.

    This abstract class provides methods for time-related operations,
    allowing implementations to be swapped for testing or different
    time sources. Use RealClock for production code and SyntheticClock
    for testing.

    Example:
        >>> clock = RealClock()
        >>> current_time = clock.time()
        >>> clock.sleep(1.0)  # Sleep for 1 second
        >>> timer = clock.start_timer(5.0, callback, repeat=True)
    """

    @abstractmethod
    def time(self) -> float:
        """Get current time as seconds since epoch.

        Returns:
            Current time as float
        """
        pass

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        """Sleep for specified duration.

        Args:
            seconds: Duration to sleep
        """
        pass

    @abstractmethod
    def monotonic(self) -> float:
        """Get monotonic time (not affected by system clock adjustments).

        Returns:
            Monotonic time as float
        """
        pass

    @abstractmethod
    def thread_sleep(self, seconds: float) -> None:
        """Sleep in current thread.

        Args:
            seconds: Duration to sleep
        """
        pass

    @abstractmethod
    def start_timer(
        self, interval: float, callback: Callable[[], None], repeat: bool = False
    ) -> "Timer":
        """Start a timer that calls callback after interval.

        Args:
            interval: Time interval in seconds
            callback: Function to call
            repeat: If True, timer repeats

        Returns:
            Timer object
        """
        pass


class Timer(ABC):
    """Abstract timer interface.

    Timers are created by Clock implementations and can be used to
    schedule callbacks at specific intervals. Timers can be one-shot
    or repeating.

    Example:
        >>> clock = RealClock()
        >>> def my_callback():
        ...     print("Timer fired!")
        >>> timer = clock.start_timer(5.0, my_callback, repeat=False)
        >>> # ... later ...
        >>> timer.cancel()  # Cancel if needed
    """

    @abstractmethod
    def cancel(self) -> None:
        """Cancel the timer.

        Returns:
            None
        """
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Check if timer is still active.

        Returns:
            True if active, False otherwise
        """
        pass


class RealClock(Clock):
    """Real clock implementation using standard library.

    This is the production implementation that uses Python's built-in
    time and threading modules to provide actual system clock time
    and real sleep operations.

    Example:
        >>> clock = RealClock()
        >>> start = clock.time()
        >>> clock.sleep(0.1)  # Actually sleeps for 0.1 seconds
        >>> elapsed = clock.time() - start
        >>> assert elapsed >= 0.1
    """

    def time(self) -> float:
        """Get current time as seconds since epoch.

        Returns:
            Current time as float (seconds since Unix epoch)
        """
        return time.time()

    def sleep(self, seconds: float) -> None:
        """Sleep for specified duration.

        Args:
            seconds: Duration to sleep in seconds
        """
        time.sleep(seconds)

    def monotonic(self) -> float:
        """Get monotonic time (not affected by system clock adjustments).

        Returns:
            Monotonic time as float (seconds since an arbitrary point)
        """
        return time.monotonic()

    def thread_sleep(self, seconds: float) -> None:
        """Sleep in current thread.

        Args:
            seconds: Duration to sleep in seconds
        """
        threading.Event().wait(seconds)

    def start_timer(
        self, interval: float, callback: Callable[[], None], repeat: bool = False
    ) -> "Timer":
        """Start a timer using threading.Timer.

        Args:
            interval: Time interval in seconds before callback is called
            callback: Function to call when timer fires
            repeat: If True, timer will repeat after each interval

        Returns:
            Timer object that can be used to cancel the timer
        """
        timer = threading.Timer(interval, callback)
        if repeat:
            # For repeat, we need to reschedule
            def repeat_callback():
                callback()
                if timer.is_alive():  # Only reschedule if not cancelled
                    timer.interval = interval
                    timer.start()

            timer = threading.Timer(interval, repeat_callback)
        timer.start()
        return RealTimer(timer)


class RealTimer(Timer):
    """Real timer implementation using threading.Timer.

    This is the concrete timer returned by RealClock.start_timer().
    It wraps a threading.Timer and provides the Timer interface.
    """

    def __init__(self, timer: threading.Timer):
        """Initialize with threading.Timer.

        Args:
            timer: The threading.Timer instance to wrap
        """
        self._timer = timer

    def cancel(self) -> None:
        """Cancel the timer.

        Returns:
            None
        """
        self._timer.cancel()

    def is_active(self) -> bool:
        """Check if timer is active."""
        return self._timer.is_alive()


class SyntheticClock(Clock):
    """Synthetic clock for testing - allows manual time control.

    This implementation allows you to control time manually, making it
    easy to test time-dependent code with predictable timestamps.
    Time advances only when you call advance() or set_time().

    Example:
        >>> clock = SyntheticClock(start_time=100.0)
        >>> assert clock.time() == 100.0
        >>> clock.advance(5.0)
        >>> assert clock.time() == 105.0
        >>> clock.set_time(200.0)
        >>> assert clock.time() == 200.0
    """

    def __init__(self, start_time: float = 0.0):
        """Initialize synthetic clock.

        Args:
            start_time: Initial time value
        """
        self._time = start_time
        self._monotonic = start_time
        self._timers: list["SyntheticTimer"] = []
        self._lock = threading.Lock()

    def time(self) -> float:
        """Get current synthetic time.

        Returns:
            Current synthetic time value
        """
        with self._lock:
            return self._time

    def sleep(self, seconds: float) -> None:
        """Advance time instead of actually sleeping.

        Args:
            seconds: Amount of time to advance (does not actually sleep)
        """
        self.advance(seconds)

    def monotonic(self) -> float:
        """Get monotonic time.

        Returns:
            Monotonic time value (same as time() for synthetic clock)
        """
        with self._lock:
            return self._monotonic

    def thread_sleep(self, seconds: float) -> None:
        """Advance time instead of actually sleeping.

        Args:
            seconds: Amount of time to advance (does not actually sleep)
        """
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        """Manually advance time.

        Args:
            seconds: Amount to advance time by
        """
        with self._lock:
            self._time += seconds
            self._monotonic += seconds

            # Check and fire timers
            active_timers = []
            for timer in self._timers:
                if timer.is_active():
                    timer._check_and_fire(self._time)
                    if timer.is_active():
                        active_timers.append(timer)
            self._timers = active_timers

    def set_time(self, time_value: float) -> None:
        """Set the current time.

        Args:
            time_value: Time value to set
        """
        with self._lock:
            self._time = time_value
            self._monotonic = time_value

    def start_timer(
        self, interval: float, callback: Callable[[], None], repeat: bool = False
    ) -> "SyntheticTimer":
        """Start a synthetic timer.

        Args:
            interval: Time interval in seconds before callback is called
            callback: Function to call when timer fires
            repeat: If True, timer will repeat after each interval

        Returns:
            SyntheticTimer object that can be used to cancel the timer
        """
        timer = SyntheticTimer(self, interval, callback, repeat, self._time)
        with self._lock:
            self._timers.append(timer)
        return timer


class SyntheticTimer(Timer):
    """Synthetic timer implementation for SyntheticClock.

    This timer fires based on synthetic time rather than real time.
    It only fires when the clock's time is advanced past the fire time.
    """

    def __init__(
        self,
        clock: SyntheticClock,
        interval: float,
        callback: Callable[[], None],
        repeat: bool,
        start_time: float,
    ):
        """Initialize synthetic timer.

        Args:
            clock: The SyntheticClock instance that owns this timer
            interval: Time interval in seconds before callback fires
            callback: Function to call when timer fires
            repeat: If True, timer will repeat after each interval
            start_time: Current time when timer is created
        """
        self._clock = clock
        self._interval = interval
        self._callback = callback
        self._repeat = repeat
        self._fire_time = start_time + interval
        self._active = True

    def _check_and_fire(self, current_time: float) -> None:
        """Check if timer should fire and fire if needed."""
        if not self._active:
            return

        if current_time >= self._fire_time:
            self._callback()
            if self._repeat:
                self._fire_time = current_time + self._interval
            else:
                self._active = False

    def cancel(self) -> None:
        """Cancel the timer.

        Returns:
            None
        """
        self._active = False

    def is_active(self) -> bool:
        """Check if timer is active."""
        return self._active
