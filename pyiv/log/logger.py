"""Injectable logger emit surface."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional


class Logger(ABC):
    """Injectable diagnostic logger.

    **Why this exists:** Services should not call ``logging.getLogger`` directly
    if tests need to assert messages without patching the logging module.

    Example:
        >>> from pyiv.log import MemoryLogger
        >>> log: Logger = MemoryLogger("svc")
        >>> log.info("ready")
        >>> log.records[-1].message
        'ready'
    """

    @abstractmethod
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""

    @abstractmethod
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""

    @abstractmethod
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""

    @abstractmethod
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""

    @abstractmethod
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error with exception info."""

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log at a numeric level (default routes through info for Memory)."""
        if level >= logging.ERROR:
            self.error(msg, *args, **kwargs)
        elif level >= logging.WARNING:
            self.warning(msg, *args, **kwargs)
        elif level >= logging.INFO:
            self.info(msg, *args, **kwargs)
        else:
            self.debug(msg, *args, **kwargs)


class StdlibLogger(Logger):
    """Logger wrapping a stdlib ``logging.Logger``.

    **Why this exists:** Production emit path that still participates in the
    stdlib hierarchy (third-party libs keep working).
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(msg, *args, **kwargs)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.log(level, msg, *args, **kwargs)


@dataclass(frozen=True)
class LogRecord:
    """Captured log line for ``MemoryLogger``.

    **Why this exists:** Frozen assertion DTO.
    """

    level: str
    message: str
    name: str


class MemoryLogger(Logger):
    """In-memory logger for tests.

    **Why this exists:** Assert diagnostics without attaching handlers to root.

    Example:
        >>> log = MemoryLogger("t")
        >>> log.warning("careful")
        >>> [r.level for r in log.records]
        ['WARNING']
    """

    def __init__(self, name: str = "memory") -> None:
        self.name = name
        self.records: List[LogRecord] = []

    def _emit(self, level: str, msg: str, *args: Any) -> None:
        text = msg % args if args else msg
        self.records.append(LogRecord(level=level, message=text, name=self.name))

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._emit("DEBUG", msg, *args)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._emit("INFO", msg, *args)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._emit("WARNING", msg, *args)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._emit("ERROR", msg, *args)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._emit("ERROR", msg, *args)
