"""Configuration base class for dependency injection."""

from typing import Any, Callable, Dict, Optional, Type, Union

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
