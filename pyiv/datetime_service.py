"""DateTime service abstraction for dependency injection.

This module provides an abstract interface for datetime operations, allowing
for dependency injection and easier testing of time-dependent code.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional


class DateTimeService(ABC):
    """Abstract base class for datetime operations.
    
    This abstract class provides methods for getting the current UTC datetime,
    allowing implementations to be swapped for testing or different time sources.
    """
    
    @abstractmethod
    def now_utc(self) -> datetime:
        """Get current UTC datetime.
        
        Returns:
            Current datetime in UTC timezone
        """
        pass
    
    @abstractmethod
    def now_utc_iso(self) -> str:
        """Get current UTC datetime as ISO format string.
        
        Returns:
            Current datetime in UTC as ISO format string (e.g., "2024-01-15T10:30:00.123456+00:00")
        """
        pass


class PythonDateTimeService(DateTimeService):
    """DateTime service implementation using Python's datetime module.
    
    This is the production implementation that uses Python's built-in datetime
    module to return actual current time from the system clock.
    """
    
    def now_utc(self) -> datetime:
        """Get current UTC datetime from system clock using Python's datetime.
        
        Returns:
            Current datetime in UTC timezone
        """
        return datetime.now(timezone.utc)
    
    def now_utc_iso(self) -> str:
        """Get current UTC datetime as ISO format string using Python's datetime.
        
        Returns:
            Current datetime in UTC as ISO format string
        """
        return datetime.now(timezone.utc).isoformat()


class MockDateTimeService(DateTimeService):
    """Mock datetime service for testing.
    
    This implementation allows you to control the time returned, making it
    easy to test time-dependent code with predictable timestamps.
    
    Example:
        >>> from datetime import datetime, timezone
        >>> service = MockDateTimeService(datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc))
        >>> service.now_utc()
        datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        >>> service.set_time(datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc))
        >>> service.now_utc()
        datetime.datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    """
    
    def __init__(self, fixed_time: Optional[datetime] = None):
        """Initialize with optional fixed time.
        
        Args:
            fixed_time: Fixed datetime to return (defaults to current time if not provided)
        """
        if fixed_time is None:
            fixed_time = datetime.now(timezone.utc)
        elif fixed_time.tzinfo is None:
            # If no timezone provided, assume UTC
            fixed_time = fixed_time.replace(tzinfo=timezone.utc)
        self._fixed_time = fixed_time
    
    def now_utc(self) -> datetime:
        """Return fixed time.
        
        Returns:
            The fixed datetime set for this mock service
        """
        return self._fixed_time
    
    def now_utc_iso(self) -> str:
        """Return fixed time as ISO string.
        
        Returns:
            The fixed datetime as ISO format string
        """
        return self._fixed_time.isoformat()
    
    def set_time(self, new_time: datetime) -> None:
        """Set the fixed time.
        
        Args:
            new_time: New fixed time. If no timezone is provided, UTC is assumed.
        """
        if new_time.tzinfo is None:
            new_time = new_time.replace(tzinfo=timezone.utc)
        self._fixed_time = new_time

