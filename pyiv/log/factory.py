"""Logger factory with abbreviated display names."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Union

from pyiv.log.logger import Logger, MemoryLogger, StdlibLogger


def abbreviate_logger_name(name: str) -> str:
    """Abbreviate dotted logger names for short format lines.

    Example:
        >>> abbreviate_logger_name("pyiv.files.mount.MountFilesystem")
        'p.f.m.MountFilesystem'
    """
    parts = name.split(".")
    if len(parts) <= 1:
        return name
    *heads, tail = parts
    return ".".join(p[:1] for p in heads) + "." + tail


class LoggerFactory(ABC):
    """Create named ``Logger`` instances.

    **Why this exists:** Services ask for a named logger without binding each
    name in the injector.

    Example:
        >>> from pyiv.log import StdlibLoggerFactory
        >>> factory: LoggerFactory = StdlibLoggerFactory()
        >>> isinstance(factory.get("app.svc"), Logger)
        True
    """

    @abstractmethod
    def get(self, name: Union[str, Type[Any]]) -> Logger:
        """Return a logger for ``name`` (string or type)."""


class StdlibLoggerFactory(LoggerFactory):
    """Factory wrapping ``logging.getLogger``.

    **Why this exists:** Production factory that stays on the stdlib hierarchy.
    """

    def get(self, name: Union[str, Type[Any]]) -> Logger:
        if isinstance(name, type):
            name = f"{name.__module__}.{name.__qualname__}"
        return StdlibLogger(logging.getLogger(str(name)))


class MemoryLoggerFactory(LoggerFactory):
    """Factory that returns shared ``MemoryLogger`` instances by name.

    **Why this exists:** Tests inject one factory and assert per-name records.
    """

    def __init__(self) -> None:
        self._loggers: Dict[str, MemoryLogger] = {}

    def get(self, name: Union[str, Type[Any]]) -> Logger:
        if isinstance(name, type):
            key = f"{name.__module__}.{name.__qualname__}"
        else:
            key = str(name)
        if key not in self._loggers:
            self._loggers[key] = MemoryLogger(key)
        return self._loggers[key]
