"""Tests for datetime service abstraction."""

from datetime import datetime, timedelta, timezone

import pytest

from pyiv.datetime_service import DateTimeService, MockDateTimeService, PythonDateTimeService


def test_datetime_service_now_utc():
    """Test PythonDateTimeService.now_utc() returns current UTC time."""
    service = PythonDateTimeService()

    # Get time twice to verify it's actually getting current time
    t1 = service.now_utc()
    assert isinstance(t1, datetime)
    assert t1.tzinfo == timezone.utc

    # Small delay and get again
    import time

    time.sleep(0.01)
    t2 = service.now_utc()
    assert t2 > t1
    assert t2.tzinfo == timezone.utc


def test_datetime_service_now_utc_iso():
    """Test PythonDateTimeService.now_utc_iso() returns ISO format string."""
    service = PythonDateTimeService()

    iso_str = service.now_utc_iso()
    assert isinstance(iso_str, str)
    assert "T" in iso_str  # ISO format has T separator
    assert "+00:00" in iso_str or "Z" in iso_str  # UTC timezone indicator

    # Should be parseable
    parsed = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    assert parsed.tzinfo == timezone.utc


def test_mock_datetime_service_with_fixed_time():
    """Test MockDateTimeService with fixed time."""
    fixed_time = datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)
    service = MockDateTimeService(fixed_time)

    # Should return the fixed time
    assert service.now_utc() == fixed_time
    assert service.now_utc_iso() == fixed_time.isoformat()


def test_mock_datetime_service_defaults_to_current_time():
    """Test MockDateTimeService defaults to current time if not provided."""
    service = MockDateTimeService()

    # Should return a datetime
    result = service.now_utc()
    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc

    # Should be close to current time (within 1 second)
    now = datetime.now(timezone.utc)
    assert abs((result - now).total_seconds()) < 1.0


def test_mock_datetime_service_without_timezone():
    """Test MockDateTimeService assumes UTC if no timezone provided."""
    fixed_time = datetime(2024, 1, 15, 10, 30, 45)
    service = MockDateTimeService(fixed_time)

    # Should have UTC timezone
    result = service.now_utc()
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == fixed_time


def test_mock_datetime_service_set_time():
    """Test MockDateTimeService.set_time() changes the fixed time."""
    initial_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    service = MockDateTimeService(initial_time)

    assert service.now_utc() == initial_time

    # Set new time
    new_time = datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    service.set_time(new_time)

    assert service.now_utc() == new_time
    assert service.now_utc() != initial_time


def test_mock_datetime_service_set_time_without_timezone():
    """Test MockDateTimeService.set_time() assumes UTC if no timezone."""
    service = MockDateTimeService(datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc))

    new_time = datetime(2024, 1, 16, 12, 0, 0)
    service.set_time(new_time)

    result = service.now_utc()
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == new_time


def test_datetime_service_interface():
    """Test that both implementations satisfy the interface."""
    real_service = PythonDateTimeService()
    mock_service = MockDateTimeService()

    # Both should have the required methods
    assert hasattr(real_service, "now_utc")
    assert hasattr(real_service, "now_utc_iso")
    assert hasattr(mock_service, "now_utc")
    assert hasattr(mock_service, "now_utc_iso")

    # Both should return datetime from now_utc
    assert isinstance(real_service.now_utc(), datetime)
    assert isinstance(mock_service.now_utc(), datetime)

    # Both should return strings from now_utc_iso
    assert isinstance(real_service.now_utc_iso(), str)
    assert isinstance(mock_service.now_utc_iso(), str)


def test_mock_datetime_service_iso_format():
    """Test MockDateTimeService ISO format output."""
    fixed_time = datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)
    service = MockDateTimeService(fixed_time)

    iso_str = service.now_utc_iso()
    assert iso_str == fixed_time.isoformat()
    assert "2024-01-15T10:30:45.123456+00:00" in iso_str or "2024-01-15T10:30:45.123456Z" in iso_str


def test_datetime_service_timezone_aware():
    """Test that both services return timezone-aware datetimes."""
    real_service = PythonDateTimeService()
    mock_service = MockDateTimeService()

    real_time = real_service.now_utc()
    mock_time = mock_service.now_utc()

    # Both should be timezone-aware
    assert real_time.tzinfo is not None
    assert mock_time.tzinfo is not None

    # Both should be UTC
    assert real_time.tzinfo == timezone.utc
    assert mock_time.tzinfo == timezone.utc
