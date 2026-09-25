"""Singleton management for dependency injection.

This module provides singleton lifecycle management for the dependency
injection system. It supports both per-injector singletons and global
thread-safe singletons shared across all injector instances.

Architecture:
    - SingletonType: Enum defining singleton behavior types
    - GlobalSingletonRegistry: Thread-safe registry for global singletons

Singleton Types:
    - NONE: No singleton - new instance created each time
    - SINGLETON: Per-injector singleton - one instance per Injector
    - GLOBAL_SINGLETON: Global singleton - shared across all injectors

Usage:
    Configure singleton behavior when registering dependencies in Config:

    Example:
        >>> from pyiv import Config, get_injector
        >>> from pyiv.singleton import SingletonType
        >>> class Logger:
        ...     pass
        >>> class FileLogger(Logger):
        ...     pass
        >>> class Cache:
        ...     pass
        >>> class RedisCache(Cache):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Logger, FileLogger, singleton_type=SingletonType.SINGLETON)
        ...         self.register(Cache, RedisCache, singleton_type=SingletonType.GLOBAL_SINGLETON)
        >>> injector = get_injector(MyConfig)
        >>> injector.inject(Logger) is injector.inject(Logger)
        True
        >>> injector.inject(Cache) is get_injector(MyConfig).inject(Cache)
        True
"""

import threading
from enum import Enum
from typing import Any, Dict, Type, Union


class SingletonType(Enum):
    """Legacy enum for singleton lifecycle on ``Config.register``.

    **Why this exists:** Older call sites use ``singleton_type=...`` instead of
    a :class:`~pyiv.scope.Scope`. Prefer ``Scope`` for new code; this enum remains
    for compatibility.

    Attributes:
        NONE: No singleton behavior - new instance created each time
        SINGLETON: Per-injector singleton - one instance per Injector instance
        GLOBAL_SINGLETON: Global singleton - one instance shared across all injectors (thread-safe)

    Example:
        >>> from pyiv import Config, get_injector
        >>> class Logger:
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Logger, Logger, singleton_type=SingletonType.SINGLETON)
        >>> inj = get_injector(MyConfig)
        >>> inj.inject(Logger) is inj.inject(Logger)
        True
    """

    NONE = "none"
    SINGLETON = "singleton"
    GLOBAL_SINGLETON = "global_singleton"


class GlobalSingletonRegistry:
    """Process-wide store for ``GLOBAL_SINGLETON`` instances.

    **Why this exists:** Some resources must be unique across injectors
    (shared caches). Tests call :meth:`clear` between cases so state does
    not leak.

    Example:
        >>> class Cache:
        ...     pass
        >>> GlobalSingletonRegistry.clear()
        >>> GlobalSingletonRegistry.set(Cache, Cache())
        >>> GlobalSingletonRegistry.has(Cache)
        True
        >>> GlobalSingletonRegistry.clear()
    """

    _lock = threading.Lock()
    _instances: Dict[Union[Type, str], Any] = {}

    @classmethod
    def get(cls, key: Union[Type, str]) -> Any:
        """Get a global singleton instance.

        Args:
            cls: The class (implicit in classmethod)
            key: The abstract type or string key to retrieve

        Returns:
            The singleton instance or None if not registered
        """
        with cls._lock:
            return cls._instances.get(key)

    @classmethod
    def set(cls, key: Union[Type, str], instance: Any) -> None:
        """Set a global singleton instance.

        Args:
            cls: The class (implicit in classmethod)
            key: The abstract type or string key
            instance: The instance to store
        """
        with cls._lock:
            cls._instances[key] = instance

    @classmethod
    def has(cls, key: Union[Type, str]) -> bool:
        """Check if a global singleton exists.

        Args:
            cls: The class (implicit in classmethod)
            key: The abstract type or string key to check

        Returns:
            True if a singleton exists, False otherwise
        """
        with cls._lock:
            return key in cls._instances

    @classmethod
    def clear(cls) -> None:
        """Clear all global singletons (useful for testing).

        Args:
            cls: The class (implicit in classmethod)
        """
        with cls._lock:
            cls._instances.clear()
