"""Configuration base class for dependency injection.

This module provides the Config base class that defines how dependencies
are registered and configured for the dependency injection system.

Architecture:
    - Config: Base class for dependency configuration
    - Subclasses override configure() to register dependencies

The Config class manages:
    - Type registrations (abstract -> concrete mappings)
    - Instance registrations (pre-created singletons)
    - Singleton lifecycle configuration
    - Factory function registrations

Usage:
    Create a Config subclass and override configure() to register dependencies:

    Example:
        >>> from pyiv import Config
        >>> from pyiv.singleton import SingletonType
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # Register concrete implementation
        ...         self.register(Database, PostgreSQL)
        ...         # Register with singleton lifecycle
        ...         self.register(Logger, FileLogger, singleton_type=SingletonType.SINGLETON)
        ...         # Register pre-created instance
        ...         self.register_instance(Cache, my_cache_instance)
"""

from typing import Any, Callable, Dict, Optional, Type, Union

from pyiv.serde.base import SerDe
from pyiv.singleton import SingletonType


class Config:
    """Base class for dependency injection configuration.

    Subclasses should override `configure()` to register dependencies.
    """

    def __init__(self):
        """Initialize the configuration."""
        self._registrations: Dict[Type, Union[Type, Any, Callable]] = {}
        self._instances: Dict[Type, Any] = {}
        self._singleton_types: Dict[Type, SingletonType] = {}
        # SerDe registrations: encoding_type -> implementation class
        self._serde_by_type: Dict[str, Type[SerDe]] = {}
        # SerDe registrations: name -> (implementation class, encoding_type)
        self._serde_by_name: Dict[str, tuple[Type[SerDe], str]] = {}
        # SerDe instances: name -> instance (for pre-created instances)
        self._serde_instances: Dict[str, SerDe] = {}
        # SerDe singleton configuration: name -> singleton_type
        self._serde_singleton_types: Dict[str, SingletonType] = {}
        self.configure()

    def configure(self):
        """Override this method to register dependencies.

        Example:
            def configure(self):
                self.register(AbstractClass, ConcreteClass)
                self.register_instance(Logger, my_logger_instance)
        """
        pass

    def register(
        self,
        abstract: Type,
        concrete: Union[Type, Callable],
        *,
        singleton: bool = False,
        singleton_type: SingletonType = SingletonType.NONE,
    ):
        """Register a concrete implementation for an abstract type.

        Args:
            abstract: The abstract class or interface to register
            concrete: The concrete class, instance, or factory function
            singleton: If True, uses SINGLETON type (deprecated, use singleton_type instead)
            singleton_type: Type of singleton behavior (NONE, SINGLETON, or GLOBAL_SINGLETON)

        Raises:
            TypeError: If abstract is not a type
            ValueError: If both singleton=True and singleton_type is specified
        """
        if not isinstance(abstract, type):
            raise TypeError(f"abstract must be a type, got {type(abstract)}")

        # Handle deprecated singleton parameter
        if singleton and singleton_type != SingletonType.NONE:
            raise ValueError("Cannot specify both singleton=True and singleton_type")
        if singleton:
            singleton_type = SingletonType.SINGLETON

        # Store singleton type
        if singleton_type != SingletonType.NONE:
            self._singleton_types[abstract] = singleton_type

        if singleton_type == SingletonType.SINGLETON and isinstance(concrete, type):
            # For singleton classes, we'll create an instance on first injection
            self._instances[abstract] = None  # Placeholder, will be created lazily
            self._registrations[abstract] = concrete
        elif not isinstance(concrete, type) and not callable(concrete):
            # It's an instance
            self._instances[abstract] = concrete
            self._registrations[abstract] = type(concrete)
        else:
            # It's a class or callable factory
            self._registrations[abstract] = concrete

    def register_instance(self, abstract: Type, instance: Any):
        """Register a concrete instance for an abstract type.

        Args:
            abstract: The abstract class or interface
            instance: The concrete instance to register
        """
        self._instances[abstract] = instance
        self._registrations[abstract] = type(instance)

    def get_registration(self, abstract: Type) -> Optional[Union[Type, Callable]]:
        """Get the registered concrete implementation for an abstract type.

        Args:
            abstract: The abstract class or interface

        Returns:
            The registered concrete class, callable, or None if not found
        """
        return self._registrations.get(abstract)

    def get_instance(self, abstract: Type) -> Optional[Any]:
        """Get a registered singleton instance for an abstract type.

        Args:
            abstract: The abstract class or interface

        Returns:
            The registered instance or None if not found
        """
        return self._instances.get(abstract)

    def has_registration(self, abstract: Type) -> bool:
        """Check if a registration exists for an abstract type.

        Args:
            abstract: The abstract class or interface

        Returns:
            True if registered, False otherwise
        """
        return abstract in self._registrations

    def get_singleton_type(self, abstract: Type) -> SingletonType:
        """Get the singleton type for a registered abstract type.

        Args:
            abstract: The abstract class or interface

        Returns:
            The singleton type, or SingletonType.NONE if not registered or not a singleton
        """
        return self._singleton_types.get(abstract, SingletonType.NONE)

    def register_serde(
        self,
        encoding_type: str,
        serde_class: Type[SerDe],
        *,
        singleton_type: SingletonType = SingletonType.SINGLETON,
    ):
        """Register a SerDe implementation for an encoding type.

        This registers a default implementation for the encoding type.
        When injecting by encoding type (without a specific name), this
        implementation will be used.

        Args:
            encoding_type: The encoding type identifier (e.g., "json", "msgpack", "toml")
            serde_class: The SerDe implementation class
            singleton_type: Type of singleton behavior (default: SINGLETON)

        Raises:
            TypeError: If serde_class is not a subclass of SerDe
            ValueError: If encoding_type is empty
        """
        if not isinstance(encoding_type, str) or not encoding_type:
            raise ValueError(f"encoding_type must be a non-empty string, got {encoding_type}")
        if not isinstance(serde_class, type) or not issubclass(serde_class, SerDe):
            raise TypeError(f"serde_class must be a subclass of SerDe, got {serde_class}")

        self._serde_by_type[encoding_type] = serde_class
        if singleton_type != SingletonType.NONE:
            # Use encoding_type as the name for singleton tracking
            self._serde_singleton_types[encoding_type] = singleton_type

    def register_serde_by_name(
        self,
        name: str,
        serde_class: Type[SerDe],
        encoding_type: str,
        *,
        singleton_type: SingletonType = SingletonType.SINGLETON,
    ):
        """Register a named SerDe implementation.

        This allows multiple implementations of the same encoding type
        with different behaviors (e.g., "json-grpc", "json-standard",
        "json-date-format-A", "json-date-format-B").

        Args:
            name: Unique name for this SerDe instance
            serde_class: The SerDe implementation class
            encoding_type: The encoding type identifier (e.g., "json", "msgpack")
            singleton_type: Type of singleton behavior (default: SINGLETON)

        Raises:
            TypeError: If serde_class is not a subclass of SerDe
            ValueError: If name or encoding_type is empty
        """
        if not isinstance(name, str) or not name:
            raise ValueError(f"name must be a non-empty string, got {name}")
        if not isinstance(encoding_type, str) or not encoding_type:
            raise ValueError(f"encoding_type must be a non-empty string, got {encoding_type}")
        if not isinstance(serde_class, type) or not issubclass(serde_class, SerDe):
            raise TypeError(f"serde_class must be a subclass of SerDe, got {serde_class}")

        self._serde_by_name[name] = (serde_class, encoding_type)
        if singleton_type != SingletonType.NONE:
            self._serde_singleton_types[name] = singleton_type

    def register_serde_instance(self, name: str, instance: SerDe):
        """Register a pre-created SerDe instance.

        Args:
            name: Unique name for this SerDe instance
            instance: The pre-created SerDe instance

        Raises:
            TypeError: If instance is not a SerDe
            ValueError: If name is empty
        """
        if not isinstance(name, str) or not name:
            raise ValueError(f"name must be a non-empty string, got {name}")
        if not isinstance(instance, SerDe):
            raise TypeError(f"instance must be a SerDe, got {type(instance)}")

        self._serde_instances[name] = instance
        # Also register by encoding type if not already registered
        encoding_type = instance.encoding_type
        if encoding_type not in self._serde_by_type:
            self._serde_by_type[encoding_type] = type(instance)

    def get_serde_registration(self, encoding_type: str) -> Optional[Type[SerDe]]:
        """Get the registered SerDe class for an encoding type.

        Args:
            encoding_type: The encoding type identifier

        Returns:
            The registered SerDe class, or None if not found
        """
        return self._serde_by_type.get(encoding_type)

    def get_serde_registration_by_name(self, name: str) -> Optional[tuple[Type[SerDe], str]]:
        """Get the registered SerDe class and encoding type for a name.

        Args:
            name: The SerDe instance name

        Returns:
            A tuple of (SerDe class, encoding_type), or None if not found
        """
        return self._serde_by_name.get(name)

    def get_serde_instance(self, name: str) -> Optional[SerDe]:
        """Get a pre-registered SerDe instance.

        Args:
            name: The SerDe instance name

        Returns:
            The SerDe instance, or None if not found
        """
        return self._serde_instances.get(name)

    def has_serde_registration(self, encoding_type: str) -> bool:
        """Check if a SerDe is registered for an encoding type.

        Args:
            encoding_type: The encoding type identifier

        Returns:
            True if registered, False otherwise
        """
        return encoding_type in self._serde_by_type

    def has_serde_registration_by_name(self, name: str) -> bool:
        """Check if a SerDe is registered by name.

        Args:
            name: The SerDe instance name

        Returns:
            True if registered, False otherwise
        """
        return name in self._serde_by_name or name in self._serde_instances

    def get_serde_singleton_type(self, name: str) -> SingletonType:
        """Get the singleton type for a SerDe registration.

        Args:
            name: The SerDe instance name or encoding type

        Returns:
            The singleton type, or SingletonType.NONE if not registered or not a singleton
        """
        return self._serde_singleton_types.get(name, SingletonType.NONE)
