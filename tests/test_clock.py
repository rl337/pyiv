"""Tests for Clock abstraction."""

import time

import pytest

from pyiv.clock import Clock, RealClock, SyntheticClock, Timer


def test_real_clock_time():
    """Test RealClock.time()."""
    clock = RealClock()
    t1 = clock.time()
    time.sleep(0.01)
    t2 = clock.time()

    assert t2 > t1
    assert isinstance(t1, float)
    assert isinstance(t2, float)


def test_real_clock_sleep():
    """Test RealClock.sleep()."""
    clock = RealClock()
    start = time.time()
    clock.sleep(0.1)
    elapsed = time.time() - start

    assert elapsed >= 0.1
    assert elapsed < 0.2  # Should be close to 0.1


def test_real_clock_monotonic():
    """Test RealClock.monotonic()."""
    clock = RealClock()
    t1 = clock.monotonic()
    time.sleep(0.01)
    t2 = clock.monotonic()

    assert t2 > t1


def test_synthetic_clock_basic():
    """Test basic SyntheticClock operations."""
    clock = SyntheticClock(start_time=100.0)

    assert clock.time() == 100.0
    assert clock.monotonic() == 100.0


def test_synthetic_clock_advance():
    """Test SyntheticClock.advance()."""
    clock = SyntheticClock(start_time=0.0)

    assert clock.time() == 0.0
    clock.advance(5.5)
    assert clock.time() == 5.5
    clock.advance(2.0)
    assert clock.time() == 7.5


def test_synthetic_clock_set_time():
    """Test SyntheticClock.set_time()."""
    clock = SyntheticClock(start_time=0.0)

    clock.set_time(100.0)
    assert clock.time() == 100.0

    clock.set_time(50.0)
    assert clock.time() == 50.0


def test_synthetic_clock_sleep():
    """Test SyntheticClock.sleep() advances time."""
    clock = SyntheticClock(start_time=0.0)

    assert clock.time() == 0.0
    clock.sleep(10.0)
    assert clock.time() == 10.0


def test_synthetic_clock_timer():
    """Test SyntheticClock timer functionality."""
    clock = SyntheticClock(start_time=0.0)
    call_count = [0]

    def callback():
        call_count[0] += 1

    timer = clock.start_timer(5.0, callback)
    assert timer.is_active() is True

    # Advance time but not enough to fire
    clock.advance(3.0)
    assert call_count[0] == 0

    # Advance enough to fire
    clock.advance(3.0)
    assert call_count[0] == 1
    assert timer.is_active() is False


def test_synthetic_clock_timer_repeat():
    """Test SyntheticClock repeating timer."""
    clock = SyntheticClock(start_time=0.0)
    call_count = [0]

    def callback():
        call_count[0] += 1

    timer = clock.start_timer(5.0, callback, repeat=True)

    # Fire multiple times
    clock.advance(5.0)
    assert call_count[0] == 1

    clock.advance(5.0)
    assert call_count[0] == 2

    clock.advance(5.0)
    assert call_count[0] == 3

    # Cancel timer
    timer.cancel()
    clock.advance(5.0)
    assert call_count[0] == 3  # Should not increment


def test_synthetic_clock_multiple_timers():
    """Test SyntheticClock with multiple timers."""
    clock = SyntheticClock(start_time=0.0)
    calls = []

    def callback1():
        calls.append("timer1")

    def callback2():
        calls.append("timer2")

    timer1 = clock.start_timer(5.0, callback1)
    timer2 = clock.start_timer(10.0, callback2)

    clock.advance(5.0)
    assert calls == ["timer1"]

    clock.advance(5.0)
    assert calls == ["timer1", "timer2"]


def test_real_clock_timer():
    """Test RealClock timer functionality."""
    clock = RealClock()
    call_count = [0]

    def callback():
        call_count[0] += 1

    timer = clock.start_timer(0.1, callback)
    assert timer.is_active() is True

    time.sleep(0.15)
    assert call_count[0] == 1
    assert timer.is_active() is False

