"""Injectable process environment."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Dict, Iterator, Mapping, MutableMapping, Optional


class Environment(ABC):
    """Injectable view of process environment variables.

    **Why this exists:** Mutating ``os.environ`` in tests leaks across cases.
    Depend on ``Environment`` and bind ``MemoryEnvironment`` in tests.

    Example:
        >>> from pyiv.process import MemoryEnvironment
        >>> env: Environment = MemoryEnvironment({"A": "1"})
        >>> env.get("A")
        '1'
    """

    @abstractmethod
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Return the value for ``key``, or ``default``."""

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Set ``key`` to ``value``."""

    @abstractmethod
    def unset(self, key: str) -> None:
        """Remove ``key`` if present."""

    @abstractmethod
    def as_dict(self) -> Dict[str, str]:
        """Return a snapshot mapping."""

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self.get(key) is not None

    def __iter__(self) -> Iterator[str]:
        return iter(self.as_dict())


class OsEnvironment(Environment):
    """Environment backed by ``os.environ``.

    **Why this exists:** Production binding for real process env.
    """

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, default)

    def set(self, key: str, value: str) -> None:
        os.environ[key] = value

    def unset(self, key: str) -> None:
        os.environ.pop(key, None)

    def as_dict(self) -> Dict[str, str]:
        return dict(os.environ)


class MemoryEnvironment(Environment):
    """In-memory environment for tests.

    **Why this exists:** Isolate env mutations without touching the process.

    Example:
        >>> env = MemoryEnvironment({"HOME": "/tmp"})
        >>> env.set("X", "1")
        >>> env.as_dict()["X"]
        '1'
    """

    def __init__(self, initial: Optional[Mapping[str, str]] = None) -> None:
        self._data: MutableMapping[str, str] = dict(initial or {})

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._data.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

    def unset(self, key: str) -> None:
        self._data.pop(key, None)

    def as_dict(self) -> Dict[str, str]:
        return dict(self._data)
