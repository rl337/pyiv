"""Clock abstraction for dependency injection."""

from abc import ABC, abstractmethod
import threading
import time
from typing import Callable, Optional


class Clock(ABC):
    """Abstract clock interface for time operations."""
    
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
    def start_timer(self, interval: float, callback: Callable[[], None], repeat: bool = False) -> 'Timer':
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
    """Abstract timer interface."""
    
    @abstractmethod
    def cancel(self) -> None:
        """Cancel the timer."""
        pass
    
    @abstractmethod
    def is_active(self) -> bool:
        """Check if timer is still active.
        
        Returns:
            True if active, False otherwise
        """
        pass


class RealClock(Clock):
    """Real clock implementation using standard library."""
    
    def time(self) -> float:
        """Get current time."""
        return time.time()
    
    def sleep(self, seconds: float) -> None:
        """Sleep for specified duration."""
        time.sleep(seconds)
    
    def monotonic(self) -> float:
        """Get monotonic time."""
        return time.monotonic()
    
    def thread_sleep(self, seconds: float) -> None:
        """Sleep in current thread."""
        threading.Event().wait(seconds)
    
    def start_timer(self, interval: float, callback: Callable[[], None], repeat: bool = False) -> 'Timer':
        """Start a timer using threading.Timer."""
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
    """Real timer implementation."""
    
    def __init__(self, timer: threading.Timer):
        """Initialize with threading.Timer."""
        self._timer = timer
    
    def cancel(self) -> None:
        """Cancel the timer."""
        self._timer.cancel()
    
    def is_active(self) -> bool:
        """Check if timer is active."""
        return self._timer.is_alive()


class SyntheticClock(Clock):
    """Synthetic clock for testing - allows manual time control."""
    
    def __init__(self, start_time: float = 0.0):
        """Initialize synthetic clock.
        
        Args:
            start_time: Initial time value
        """
        self._time = start_time
        self._monotonic = start_time
        self._timers: list['SyntheticTimer'] = []
        self._lock = threading.Lock()
    
    def time(self) -> float:
        """Get current synthetic time."""
        with self._lock:
            return self._time
    
    def sleep(self, seconds: float) -> None:
        """Advance time instead of actually sleeping."""
        self.advance(seconds)
    
    def monotonic(self) -> float:
        """Get monotonic time."""
        with self._lock:
            return self._monotonic
    
    def thread_sleep(self, seconds: float) -> None:
        """Advance time instead of actually sleeping."""
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
    
    def start_timer(self, interval: float, callback: Callable[[], None], repeat: bool = False) -> 'SyntheticTimer':
        """Start a synthetic timer."""
        timer = SyntheticTimer(self, interval, callback, repeat, self._time)
        with self._lock:
            self._timers.append(timer)
        return timer


class SyntheticTimer(Timer):
    """Synthetic timer implementation."""
    
    def __init__(self, clock: SyntheticClock, interval: float, callback: Callable[[], None], 
                 repeat: bool, start_time: float):
        """Initialize synthetic timer."""
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
        """Cancel the timer."""
        self._active = False
    
    def is_active(self) -> bool:
        """Check if timer is active."""
        return self._active


