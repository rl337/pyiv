"""Binder interface for fluent configuration API.

This module provides the Binder interface for configuring dependency bindings
in a fluent, decoupled way. The Binder separates the configuration API from
the implementation, making Config more testable and enabling programmatic
configuration.

**What Problem Does This Solve?**

Binders solve the configuration API design problem:
- **Fluent API**: Method chaining for readable, expressive configuration
- **Separation of Concerns**: Configuration API separated from implementation
- **Testability**: Mock binders for testing configuration logic
- **Programmatic Configuration**: Build configurations dynamically
- **Better Readability**: `binder.bind(X).to(Y).in_scope(Z)` is clearer than nested calls

**Real-World Use Cases:**
- **Dynamic Configuration**: Build configurations based on environment variables
- **Configuration Testing**: Mock binders to test configuration logic
- **Modular Configuration**: Compose configurations from multiple sources
- **Framework Integration**: Provide fluent APIs for framework-specific configuration

Architecture:
    - Binder: Protocol defining the binder interface
    - BindingBuilder: Fluent builder for configuring bindings
    - ConfigBinder: Concrete binder implementation used by Config

Usage Examples:

    Basic Fluent Configuration:
        >>> from pyiv.binder import Binder
        >>> from pyiv.scope import SingletonScope
        >>> from pyiv import Config, get_injector
        >>> 
        >>> class Database:
        ...     pass
        >>> 
        >>> class PostgreSQL(Database):
        ...     pass
        >>> 
        >>> class Logger:
        ...     pass
        >>> 
        >>> class FileLogger(Logger):
        ...     pass
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         binder = self.get_binder()
        ...         # Fluent API - easy to read and chain
        ...         binder.bind(Database).to(PostgreSQL)
        ...         binder.bind(Logger).to(FileLogger).in_scope(SingletonScope())
        >>> 
        >>> injector = get_injector(MyConfig)
        >>> db = injector.inject(Database)
        >>> isinstance(db, PostgreSQL)
        True

    Binding to Instances and Providers:
        >>> from pyiv.provider import InstanceProvider
        >>> from pyiv import Config, get_injector
        >>> 
        >>> class Cache:
        ...     def __init__(self):
        ...         self.data = {}
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         binder = self.get_binder()
        ...         # Bind to pre-created instance
        ...         cache = Cache()
        ...         binder.bind_instance(Cache, cache)
        ...         # Or use fluent API
        ...         binder.bind(Cache).to_instance(cache)
        >>> 
        >>> injector = get_injector(MyConfig)
        >>> injected_cache = injector.inject(Cache)
        >>> injected_cache is cache
        True
"""

from typing import Any, Generic, Protocol, Type, TypeVar

from pyiv.key import Key
from pyiv.provider import Provider
from pyiv.scope import Scope

T = TypeVar("T")


class BindingBuilder(Generic[T]):
    """Fluent builder for configuring bindings.

    This builder provides a fluent API for configuring how a type should
    be bound. It supports chaining methods to configure the binding.

    Example:
        >>> binder.bind(Database).to(PostgreSQL).in_scope(SingletonScope())
    """

    def to(self, implementation: Type[T]) -> "BindingBuilder[T]":
        """Bind to a concrete implementation.

        Args:
            implementation: The concrete class to bind to

        Returns:
            Self for method chaining
        """
        ...

    def to_instance(self, instance: T) -> "BindingBuilder[T]":
        """Bind to a pre-created instance.

        Args:
            instance: The instance to bind to

        Returns:
            Self for method chaining
        """
        ...

    def to_provider(self, provider: Provider[T]) -> "BindingBuilder[T]":
        """Bind to a provider.

        Args:
            provider: The provider to use for instance creation

        Returns:
            Self for method chaining
        """
        ...

    def in_scope(self, scope: Scope) -> "BindingBuilder[T]":
        """Set the scope for this binding.

        Args:
            scope: The scope to use

        Returns:
            Self for method chaining
        """
        ...


class Binder(Protocol):
    """Protocol for binder implementations.

    Binders provide a fluent API for configuring dependency bindings.
    They separate the configuration API from the implementation, making
    Config more testable and enabling programmatic configuration.

    Example:
        class MyBinder(Binder):
            def bind(self, abstract):
                return BindingBuilder(...)
    """

    def bind(self, abstract: Type[T]) -> BindingBuilder[T]:
        """Start a binding configuration.

        Args:
            abstract: The abstract type to bind

        Returns:
            A binding builder for fluent configuration
        """
        ...

    def bind_key(self, key: Key[T]) -> BindingBuilder[T]:
        """Start a binding configuration with a qualified key.

        Args:
            key: The qualified key to bind

        Returns:
            A binding builder for fluent configuration
        """
        ...

    def bind_instance(self, abstract: Type[T], instance: T) -> None:
        """Bind to a pre-created instance.

        Args:
            abstract: The abstract type
            instance: The pre-created instance
        """
        ...

    def install(self, config: Any) -> None:
        """Install another configuration module.

        Args:
            config: Another Config instance to install
        """
        ...

