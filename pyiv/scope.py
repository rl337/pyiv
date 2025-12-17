"""Scope interface for dependency lifecycle management.

This module provides the Scope interface for managing object lifecycles in
dependency injection. Scopes control when instances are created, cached, and
reused. This is a generalization of the singleton pattern, allowing for
custom scopes like request-scoped, thread-scoped, session-scoped, etc.

**What Problem Does This Solve?**

Scopes solve the lifecycle management problem in DI:
- **Singleton Pattern Generalization**: Beyond simple singletons, support request-scoped,
  thread-scoped, session-scoped, and custom lifecycles
- **Resource Management**: Control when expensive objects are created and destroyed
- **Test Isolation**: Different scopes for test vs production (e.g., per-injector vs global)
- **Thread Safety**: GlobalSingletonScope provides thread-safe singleton access
- **Extensibility**: Create custom scopes for framework-specific needs (e.g., Flask request scope)

**Real-World Use Cases:**
- **Request-Scoped**: Database connections that live for the duration of an HTTP request
- **Session-Scoped**: User session objects that persist across multiple requests
- **Thread-Scoped**: Thread-local storage for multi-threaded applications
- **Global Singletons**: Configuration objects shared across the entire application

Architecture:
    - Scope: Protocol defining the scope interface
    - NoScope: No caching - new instance every time
    - SingletonScope: Per-injector singleton scope
    - GlobalSingletonScope: Global singleton scope (thread-safe)

Usage Examples:

    Using SingletonScope (Per-Injector):
        >>> from pyiv.scope import SingletonScope
        >>> from pyiv import Config, get_injector
        >>> 
        >>> class Database:
        ...     def __init__(self):
        ...         self.connections = []
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # Per-injector singleton - each injector gets its own instance
        ...         self.register(Database, Database, scope=SingletonScope())
        >>> 
        >>> injector1 = get_injector(MyConfig)
        >>> injector2 = get_injector(MyConfig)
        >>> 
        >>> db1 = injector1.inject(Database)
        >>> db2 = injector1.inject(Database)
        >>> db3 = injector2.inject(Database)
        >>> 
        >>> # Same injector returns same instance
        >>> db1 is db2
        True
        >>> # Different injectors get different instances
        >>> db1 is not db3
        True

    Using GlobalSingletonScope (Shared Across All Injectors):
        >>> from pyiv.scope import GlobalSingletonScope
        >>> from pyiv import Config, get_injector
        >>> 
        >>> class Cache:
        ...     def __init__(self):
        ...         self.data = {}
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # Global singleton - shared across all injectors
        ...         self.register(Cache, Cache, scope=GlobalSingletonScope())
        >>> 
        >>> injector1 = get_injector(MyConfig)
        >>> injector2 = get_injector(MyConfig)
        >>> 
        >>> cache1 = injector1.inject(Cache)
        >>> cache2 = injector2.inject(Cache)
        >>> 
        >>> # All injectors share the same instance
        >>> cache1 is cache2
        True

    Using NoScope (New Instance Every Time):
        >>> from pyiv.scope import NoScope
        >>> from pyiv import Config, get_injector
        >>> 
        >>> class Logger:
        ...     def __init__(self):
        ...         self.messages = []
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # No caching - new instance every time
        ...         self.register(Logger, Logger, scope=NoScope())
        >>> 
        >>> injector = get_injector(MyConfig)
        >>> logger1 = injector.inject(Logger)
        >>> logger2 = injector.inject(Logger)
        >>> 
        >>> # Each injection creates a new instance
        >>> logger1 is not logger2
        True
"""

import threading
from typing import Any, Callable, Dict, Generic, Protocol, Type, TypeVar, Union

from pyiv.provider import Provider

T = TypeVar("T")
Key = Union[Type, str, tuple]


class Scope(Protocol):
    """Protocol for scope implementations.

    Scopes control the lifecycle of instances created by the dependency
    injection system. A scope can cache instances, create new ones on
    demand, or implement custom lifecycle logic.

    Scopes are more flexible than simple singletons - they can implement
    request-scoped, thread-scoped, session-scoped, or any custom lifecycle.

    Example:
        class RequestScope(Scope):
            def __init__(self):
                self._request_cache = {}
            
            def scope(self, key, provider):
                request_id = get_current_request_id()
                cache_key = (key, request_id)
                if cache_key not in self._request_cache:
                    self._request_cache[cache_key] = provider.get()
                return lambda: self._request_cache[cache_key]
    """

    def scope(self, key: Key, provider: Provider[Any]) -> Provider[Any]:
        """Scope a provider to this scope's lifecycle.

        Args:
            key: The key identifying the dependency (Type, str, or tuple)
            provider: The provider to scope

        Returns:
            A new provider that respects this scope's lifecycle
        """
        ...


class NoScope:
    """No scope - creates a new instance every time.

    This scope does not cache instances. Each call to get() will create
    a new instance. This is the default behavior when no scope is specified.

    Example:
        >>> from pyiv.scope import NoScope
        >>> from pyiv import Config
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # No caching - new instance every time
        ...         self.register(Logger, FileLogger, scope=NoScope())
    """

    def scope(self, key: Key, provider: Provider[Any]) -> Provider[Any]:
        """Return the provider unchanged (no caching).

        Args:
            key: The key identifying the dependency
            provider: The provider to scope

        Returns:
            The same provider (no caching)
        """
        return provider


class SingletonScope:
    """Per-injector singleton scope.

    This scope caches instances per injector. Each injector will have its
    own singleton instance. This is useful when you want singletons but
    need different instances for different injectors (e.g., test vs production).

    Example:
        >>> from pyiv.scope import SingletonScope
        >>> from pyiv import Config
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # Per-injector singleton
        ...         self.register(Logger, FileLogger, scope=SingletonScope())
    """

    def __init__(self):
        """Initialize the singleton scope."""
        self._instances: Dict[Key, Any] = {}

    def scope(self, key: Key, provider: Provider[Any]) -> Provider[Any]:
        """Scope provider to per-injector singleton.

        Args:
            key: The key identifying the dependency
            provider: The provider to scope

        Returns:
            A provider that returns the same instance for this scope
        """
        def scoped_provider() -> Any:
            if key not in self._instances:
                self._instances[key] = provider.get()
            return self._instances[key]

        return scoped_provider


class GlobalSingletonScope:
    """Global singleton scope (thread-safe).

    This scope caches instances globally across all injectors. The same
    instance is shared by all injectors and all threads. Access is thread-safe.

    This is useful for truly global singletons like configuration, caches,
    or shared resources.

    Example:
        >>> from pyiv.scope import GlobalSingletonScope
        >>> from pyiv import Config
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # Global singleton (shared across all injectors)
        ...         self.register(Cache, RedisCache, scope=GlobalSingletonScope())
    """

    _lock = threading.Lock()
    _instances: Dict[Key, Any] = {}

    def scope(self, key: Key, provider: Provider[Any]) -> Provider[Any]:
        """Scope provider to global singleton.

        Args:
            key: The key identifying the dependency
            provider: The provider to scope

        Returns:
            A provider that returns the same global instance (thread-safe)
        """
        def scoped_provider() -> Any:
            with GlobalSingletonScope._lock:
                if key not in GlobalSingletonScope._instances:
                    GlobalSingletonScope._instances[key] = provider.get()
                return GlobalSingletonScope._instances[key]

        return scoped_provider

    @classmethod
    def clear(cls) -> None:
        """Clear all global singleton instances (useful for testing).

        Args:
            cls: The class (implicit in classmethod)
        """
        with cls._lock:
            cls._instances.clear()

    @classmethod
    def has(cls, key: Key) -> bool:
        """Check if a global singleton exists.

        Args:
            cls: The class (implicit in classmethod)
            key: The key to check

        Returns:
            True if a singleton exists, False otherwise
        """
        with cls._lock:
            return key in cls._instances

