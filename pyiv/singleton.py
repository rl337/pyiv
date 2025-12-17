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
        >>> from pyiv import Config
        >>> from pyiv.singleton import SingletonType
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # Per-injector singleton
        ...         self.register(Logger, FileLogger, singleton_type=SingletonType.SINGLETON)
        ...         # Global singleton (shared across all injectors)
        ...         self.register(Cache, RedisCache, singleton_type=SingletonType.GLOBAL_SINGLETON)
"""

import threading
from enum import Enum
from typing import Any, Dict, Type, Union


class SingletonType(Enum):
    """Type of singleton behavior for registered dependencies.

    Attributes:
        NONE: No singleton behavior - new instance created each time
        SINGLETON: Per-injector singleton - one instance per Injector instance
        GLOBAL_SINGLETON: Global singleton - one instance shared across all injectors (thread-safe)
    """

    NONE = "none"
    SINGLETON = "singleton"
    GLOBAL_SINGLETON = "global_singleton"


class GlobalSingletonRegistry:
    """Thread-safe registry for global singletons.

    This registry stores singleton instances that are shared across
    all injector instances. Access is thread-safe.

    Supports both Type keys (for standard DI) and string keys (for SerDe
    and other named instances).
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
