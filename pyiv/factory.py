"""Factory pattern support for dependency injection.

This module provides factory interfaces and implementations for creating
objects with dependencies. Factories are useful when object creation
requires complex logic or when you need to create multiple instances
with different configurations.

Architecture:
    - Factory: Protocol defining the factory interface (generic)
    - BaseFactory: Abstract base class for factory implementations
    - SimpleFactory: Concrete factory wrapping a callable

Usage:
    Use Factory protocol for type hints, BaseFactory for class-based
    factories, or SimpleFactory for quick function-based factories.

    Example:
        >>> from pyiv.factory import SimpleFactory, BaseFactory
        >>> class User:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>> def create_user(name: str) -> User:
        ...     return User(name=name)
        >>> factory = SimpleFactory(create_user)
        >>> factory.create("Alice").name
        'Alice'
        >>> class UserFactory(BaseFactory[User]):
        ...     def create(self, name: str) -> User:
        ...         return User(name=name)
        >>> UserFactory().create("Bob").name
        'Bob'
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Optional, Protocol, TypeVar

T = TypeVar("T", covariant=True)


class Factory(Protocol, Generic[T]):
    """Callable creation API for objects that need runtime arguments.

    **Why this exists:** A DI ``Provider`` builds one graph-managed instance.
    A ``Factory`` creates many instances with caller-supplied args (user id,
    connection string) while still allowing the factory itself to be injected.

    Example:
        >>> from pyiv.factory import SimpleFactory
        >>> class User:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>> factory: Factory[User] = SimpleFactory(User)
        >>> factory.create(name="Ada").name
        'Ada'
    """

    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create an instance of type T.

        Args:
            *args: Positional arguments for instance creation
            **kwargs: Keyword arguments for instance creation

        Returns:
            An instance of type T
        """
        ...


class BaseFactory(ABC, Generic[T]):
    """ABC when you want a class-based factory with constructor injection.

    **Why this exists:** Protocols are fine for typing; subclassing
    ``BaseFactory`` gives a real type the injector can construct, with
    dependencies supplied to ``__init__`` and runtime args to ``create``.

    Example:
        >>> from pyiv.factory import BaseFactory
        >>> class User:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>> class UserFactory(BaseFactory[User]):
        ...     def create(self, name: str) -> User:
        ...         return User(name=name)
        >>> UserFactory().create("Ada").name
        'Ada'
    """

    @abstractmethod
    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create an instance of type T.

        Args:
            *args: Positional arguments for instance creation
            **kwargs: Keyword arguments for instance creation

        Returns:
            An instance of type T
        """
        pass


class SimpleFactory(Generic[T]):
    """Simple factory that wraps a callable.

    **Why this exists:** Wrap a function/constructor as a Factory without defining a subclass.

    Useful for creating factories from functions or constructors
    without needing to define a full class.

    Example:
        >>> class User:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>> def create_user(name: str) -> User:
        ...     return User(name=name)
        >>> from pyiv.factory import SimpleFactory
        >>> factory = SimpleFactory(create_user)
        >>> factory.create("Alice").name
        'Alice'
    """

    def __init__(self, callable_factory: Callable[..., T]):
        """Initialize factory with a callable.

        Args:
            callable_factory: A callable (function, class, etc.) that creates instances
        """
        self._callable = callable_factory

    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create an instance using the wrapped callable.

        Args:
            *args: Positional arguments passed to the callable
            **kwargs: Keyword arguments passed to the callable

        Returns:
            An instance created by the callable
        """
        return self._callable(*args, **kwargs)
