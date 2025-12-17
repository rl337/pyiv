"""OptionalBinder for Optional[T] dependency support.

This module provides support for Optional[T] type hints in dependency injection.
When a dependency is marked as Optional[T], the injector will inject the
dependency if available, or None if not registered.

**What Problem Does This Solve?**

Optional dependencies solve the "graceful degradation" problem:
- **Feature Flags**: Support optional features that may or may not be available
- **Plugin Systems**: Optional plugins that enhance functionality if present
- **Environment-Specific Dependencies**: Different dependencies in dev vs production
- **Backward Compatibility**: Add new optional dependencies without breaking existing code
- **Type Safety**: Use Optional[T] instead of manual None checks

**Real-World Use Cases:**
- **Optional Caching**: Cache service that may or may not be available
- **Optional Monitoring**: Metrics/analytics that are optional in development
- **Optional Plugins**: Third-party integrations that may not be installed
- **Feature Toggles**: Features that can be enabled/disabled via configuration

Architecture:
    - OptionalBinder: Helper for binding optional dependencies
    - OptionalProvider: Provider that handles Optional[T] types

Usage Examples:

    Basic Optional Dependency:
        >>> from typing import Optional
        >>> from pyiv import Config, get_injector
        >>> 
        >>> class Database:
        ...     pass
        >>> 
        >>> class Cache:
        ...     def get(self, key: str):
        ...         return f"cached:{key}"
        >>> 
        >>> class Service:
        ...     def __init__(self, db: Database, cache: Optional[Cache] = None):
        ...         self.db = db
        ...         self.cache = cache  # Will be None if Cache not registered
        ...     
        ...     def process(self, key: str):
        ...         if self.cache:
        ...             return self.cache.get(key)
        ...         return f"no-cache:{key}"
        >>> 
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, Database)
        ...         # Cache is optional - not registered, so will be None
        >>> 
        >>> injector = get_injector(MyConfig)
        >>> service = injector.inject(Service)
        >>> service.cache is None
        True
        >>> service.process("test")
        'no-cache:test'

    Optional Dependency with Registration:
        >>> class MyConfigWithCache(Config):
        ...     def configure(self):
        ...         self.register(Database, Database)
        ...         self.register(Cache, Cache)  # Now cache is available
        >>> 
        >>> injector = get_injector(MyConfigWithCache)
        >>> service = injector.inject(Service)
        >>> service.cache is not None
        True
        >>> service.process("test")
        'cached:test'
"""

from typing import Any, Generic, Optional, Type, TypeVar, Union, get_args, get_origin

from pyiv.provider import Provider

T = TypeVar("T")


class OptionalProvider(Generic[T]):
    """Provider that handles Optional[T] types.

    This provider wraps another provider and returns None if the underlying
    provider cannot provide an instance, otherwise returns the instance.

    Example:
        >>> from pyiv.optional import OptionalProvider
        >>> from pyiv.provider import InjectorProvider
        >>> 
        >>> cache_provider = OptionalProvider(InjectorProvider(Cache, injector))
        >>> cache = cache_provider.get()  # Returns Cache instance or None
    """

    def __init__(self, provider: Provider[T], injector: Any):
        """Initialize optional provider.

        Args:
            provider: The underlying provider
            injector: The injector to use for checking availability
        """
        self._provider = provider
        self._injector = injector

    def get(self) -> Optional[T]:
        """Get an instance, or None if not available.

        Returns:
            An instance of type T, or None if not available
        """
        try:
            return self._provider.get()
        except (ValueError, TypeError):
            return None


def is_optional_type(annotation: Any) -> bool:
    """Check if a type annotation is Optional[T].

    Args:
        annotation: The type annotation to check

    Returns:
        True if the annotation is Optional[T], False otherwise
    """
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        # Optional[T] is Union[T, None] or Union[T, NoneType]
        return len(args) == 2 and type(None) in args
    return False


def get_optional_type(annotation: Any) -> Optional[Type]:
    """Extract the inner type from Optional[T].

    Args:
        annotation: The Optional[T] annotation

    Returns:
        The inner type T, or None if not Optional
    """
    if not is_optional_type(annotation):
        return None

    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        # Return the non-None type
        for arg in args:
            if arg is not type(None):
                return arg
    return None

