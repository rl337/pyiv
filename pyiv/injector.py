"""Injector implementation for dependency injection.

This module contains the core dependency injection engine. The Injector
class is responsible for creating instances, resolving dependencies,
and managing singleton lifecycles based on configuration.

Architecture:
    - Injector: Main dependency injection engine
    - get_injector(): Factory function for creating injectors from Config

The injector uses type annotations and Config registrations to automatically
resolve dependencies. It supports:
    - Constructor injection via type annotations
    - Singleton lifecycle management
    - Factory functions for complex object creation
    - Circular dependency detection

Usage:
    Create a Config subclass, register dependencies, then create an injector:

    Example:
        >>> from pyiv import Config, Injector, get_injector
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, PostgreSQL)
        ...         self.register(Logger, FileLogger, singleton=True)
        >>> injector = get_injector(MyConfig)
        >>> db = injector.inject(Database)
        >>> logger = injector.inject(Logger)
"""

import inspect
from typing import Any, Callable, Dict, Optional, Type, Union

from pyiv.config import Config
from pyiv.serde.base import SerDe
from pyiv.singleton import GlobalSingletonRegistry, SingletonType


class Injector:
    """Dependency injector that creates instances based on configuration."""

    def __init__(self, config: Config):
        """Initialize the injector with a configuration.

        Args:
            config: The configuration object that defines dependencies
        """
        self._config = config
        self._singletons: Dict[Type, Any] = {}
        self._serde_singletons: Dict[str, SerDe] = {}

    def inject(self, cls: Type, **kwargs) -> Any:
        """Inject and create an instance of the given class.

        Args:
            cls: The class to instantiate (can be abstract or concrete)
            **kwargs: Additional keyword arguments to pass to the constructor

        Returns:
            An instance of the class (or registered concrete implementation)

        Raises:
            ValueError: If no registration exists for an abstract class
            TypeError: If the registered concrete is not instantiable
        """
        # Check singleton type
        singleton_type = self._config.get_singleton_type(cls)

        # Handle global singleton
        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            instance = GlobalSingletonRegistry.get(cls)
            if instance is not None:
                return instance
            # Create new instance and store globally
            concrete = self._config.get_registration(cls)
            if concrete is None:
                instance = self._instantiate(cls, **kwargs)
            else:
                instance = self._instantiate(concrete, **kwargs)
            GlobalSingletonRegistry.set(cls, instance)
            return instance

        # Check if we have a registered singleton instance
        instance = self._config.get_instance(cls)
        if instance is not None:
            return instance

        # Check if we have a cached per-injector singleton
        if singleton_type == SingletonType.SINGLETON and cls in self._singletons:
            return self._singletons[cls]

        # Get the concrete implementation
        concrete = self._config.get_registration(cls)

        if concrete is None:
            # No registration, try to instantiate the class directly
            # (useful for concrete classes that don't need registration)
            instance = self._instantiate(cls, **kwargs)
            # Store as singleton if configured
            if singleton_type == SingletonType.SINGLETON:
                self._singletons[cls] = instance
            return instance

        # Check if it's a lazy singleton registration (old style)
        if cls in self._config._instances and self._config._instances[cls] is None:
            # Lazy singleton creation
            instance = self._instantiate(concrete, **kwargs)
            self._singletons[cls] = instance
            self._config._instances[cls] = instance
            return instance

        # Instantiate the concrete implementation
        instance = self._instantiate(concrete, **kwargs)

        # Store as singleton if configured
        if singleton_type == SingletonType.SINGLETON:
            self._singletons[cls] = instance
        elif cls in self._config._instances:
            # Old-style singleton caching
            self._singletons[cls] = instance

        return instance

    def _instantiate(self, concrete: Union[Type, Callable[..., Any]], **kwargs) -> Any:
        """Instantiate a class or call a factory function.

        Args:
            concrete: The class or callable to instantiate
            **kwargs: Keyword arguments for the constructor

        Returns:
            An instance of the class or result of the callable
        """
        if callable(concrete) and not isinstance(concrete, type):
            # It's a factory function
            sig = inspect.signature(concrete)
            # Special case: if factory function accepts 'injector' parameter, pass self
            # Do this before resolving dependencies so it's available
            if "injector" in sig.parameters:
                kwargs["injector"] = self
            # Try to inject dependencies from the function signature
            bound_kwargs = self._resolve_dependencies(sig, kwargs)
            return concrete(**bound_kwargs)
        elif isinstance(concrete, type):
            # It's a class
            sig = inspect.signature(concrete.__init__)  # type: ignore[misc]
            bound_kwargs = self._resolve_dependencies(sig, kwargs)
            return concrete(**bound_kwargs)
        else:
            raise TypeError(f"Cannot instantiate {concrete}, must be a class or callable")

    def _resolve_dependencies(
        self, sig: inspect.Signature, provided_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve dependencies from function signature using the injector.

        Args:
            sig: The function signature
            provided_kwargs: Explicitly provided keyword arguments

        Returns:
            A dictionary of resolved keyword arguments
        """
        resolved = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Skip varargs and varkwargs - they're handled separately
            if param.kind == inspect.Parameter.VAR_POSITIONAL:  # *args
                continue
            if param.kind == inspect.Parameter.VAR_KEYWORD:  # **kwargs
                continue

            # If explicitly provided, use that
            if param_name in provided_kwargs:
                resolved[param_name] = provided_kwargs[param_name]
                continue

            # Check if there's a type annotation
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation

                # Special case: if parameter is named 'injector' and type is Injector, use self
                if param_name == "injector" and annotation == Injector:
                    resolved[param_name] = self
                    continue

                # Only try to inject if it's a registered type (not built-in types)
                # Built-in types like str, int, etc. should use their defaults
                is_builtin = annotation in (
                    str,
                    int,
                    float,
                    bool,
                    bytes,
                    list,
                    dict,
                    tuple,
                    set,
                    frozenset,
                )
                is_registered = not is_builtin and self._config.has_registration(annotation)

                if is_registered:
                    # Try to inject this dependency
                    try:
                        resolved[param_name] = self.inject(annotation)
                        continue
                    except (ValueError, TypeError):
                        # Can't inject, will use default if available
                        pass

            # Use default value if available
            if param.default != inspect.Parameter.empty:
                resolved[param_name] = param.default
            elif param_name not in resolved:
                # Required parameter not provided and can't be injected
                raise ValueError(f"Missing required parameter '{param_name}' for {sig}")

        return resolved

    def inject_by_name(self, interface: Type, name: str) -> Type:
        """Inject a specific implementation by name.

        This method is used with reflection-based discovery to get a specific
        implementation class by its discovered name. The class is returned
        (not instantiated) - use inject() to get an instance.

        Args:
            interface: The interface type
            name: Implementation name (e.g., "CreateFactHandler" or "handlers.CreateFactHandler")

        Returns:
            The implementation class

        Raises:
            ValueError: If no implementation with the given name is found
            TypeError: If interface is not a type

        Example:
            # Get handler class by name
            handler_class = injector.inject_by_name(IMcpToolHandler, "CreateFactHandler")

            # Get instance (respects singleton configuration)
            handler_instance = injector.inject(handler_class)
        """
        if not isinstance(interface, type):
            raise TypeError(f"interface must be a type, got {type(interface)}")

        # Check if config supports reflection-based discovery
        if not hasattr(self._config, "discover_implementations"):
            raise ValueError(
                f"Config {type(self._config).__name__} does not support reflection-based discovery. "
                "Use ReflectionConfig for inject_by_name() support."
            )

        # Get discovered implementations
        implementations = self._config.discover_implementations(interface)

        if name not in implementations:
            available = ", ".join(sorted(implementations.keys())) or "none"
            raise ValueError(
                f"No implementation '{name}' found for {interface.__name__}. "
                f"Available implementations: {available}"
            )

        # Return the class (not instance)
        # The caller will use inject() which respects singleton configuration
        return implementations[name]

    def inject_serde(self, encoding_type: str) -> SerDe:
        """Inject a SerDe instance by encoding type.

        Returns the default SerDe implementation for the given encoding type.
        Respects singleton configuration.

        Args:
            encoding_type: The encoding type identifier (e.g., "json", "msgpack")

        Returns:
            A SerDe instance

        Raises:
            ValueError: If no SerDe is registered for the encoding type

        Example:
            >>> injector = get_injector(MyConfig)
            >>> json_serde = injector.inject_serde("json")
            >>> data = json_serde.serialize({"key": "value"})
        """
        # Check for pre-registered instance
        instance = self._config.get_serde_instance(encoding_type)
        if instance is not None:
            return instance

        # Get the registered class
        serde_class = self._config.get_serde_registration(encoding_type)
        if serde_class is None:
            available = ", ".join(sorted(self._config._serde_by_type.keys())) or "none"
            raise ValueError(
                f"No SerDe registered for encoding type '{encoding_type}'. "
                f"Available types: {available}"
            )

        # Check singleton configuration
        singleton_type = self._config.get_serde_singleton_type(encoding_type)

        # Handle global singleton
        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            # Use encoding_type as the key for global registry
            key = f"serde:{encoding_type}"
            instance = GlobalSingletonRegistry.get(key)
            if instance is not None:
                return instance
            # Create new instance
            instance = self._instantiate(serde_class)
            GlobalSingletonRegistry.set(key, instance)
            return instance

        # Check if we have a cached per-injector singleton
        if singleton_type == SingletonType.SINGLETON and encoding_type in self._serde_singletons:
            return self._serde_singletons[encoding_type]

        # Create instance
        instance = self._instantiate(serde_class)

        # Store as singleton if configured
        if singleton_type == SingletonType.SINGLETON:
            self._serde_singletons[encoding_type] = instance

        return instance

    def inject_serde_by_name(self, name: str) -> SerDe:
        """Inject a SerDe instance by name.

        Returns a named SerDe implementation. This allows multiple instances
        of the same encoding type with different behaviors (e.g., different
        date formatting, gRPC compatibility, etc.).

        Args:
            name: The SerDe instance name

        Returns:
            A SerDe instance

        Raises:
            ValueError: If no SerDe is registered with the given name

        Example:
            >>> injector = get_injector(MyConfig)
            >>> grpc_serde = injector.inject_serde_by_name("json-grpc")
            >>> input_serde = injector.inject_serde_by_name("json-input")
            >>> output_serde = injector.inject_serde_by_name("json-output")
        """
        # Check for pre-registered instance
        instance = self._config.get_serde_instance(name)
        if instance is not None:
            return instance

        # Get the registered class and encoding type
        registration = self._config.get_serde_registration_by_name(name)
        if registration is None:
            available = ", ".join(sorted(self._config._serde_by_name.keys())) or "none"
            raise ValueError(
                f"No SerDe registered with name '{name}'. " f"Available names: {available}"
            )

        serde_class, encoding_type = registration

        # Check singleton configuration
        singleton_type = self._config.get_serde_singleton_type(name)

        # Handle global singleton
        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            key = f"serde:{name}"
            instance = GlobalSingletonRegistry.get(key)
            if instance is not None:
                return instance
            # Create new instance
            instance = self._instantiate(serde_class)
            GlobalSingletonRegistry.set(key, instance)
            return instance

        # Check if we have a cached per-injector singleton
        if singleton_type == SingletonType.SINGLETON and name in self._serde_singletons:
            return self._serde_singletons[name]

        # Create instance
        instance = self._instantiate(serde_class)

        # Store as singleton if configured
        if singleton_type == SingletonType.SINGLETON:
            self._serde_singletons[name] = instance

        return instance


def get_injector(config: Union[Type[Config], Config]) -> Injector:
    """Create an injector from a configuration class or instance.

    Args:
        config: A Config subclass or Config instance that defines dependencies

    Returns:
        An Injector instance configured with the given config

    Example:
        # Using a Config class
        class MyConfig(Config):
            def configure(self):
                self.register(Database, PostgreSQL)

        injector = get_injector(MyConfig)
        db = injector.inject(Database)

        # Using a Config instance (useful for test configs with parameters)
        test_config = MyTestConfig(mock_db=my_mock)
        injector = get_injector(test_config)
        db = injector.inject(Database)
    """
    if isinstance(config, Config):
        # Already an instance, use it directly
        return Injector(config)
    elif isinstance(config, type) and issubclass(config, Config):
        # It's a class, instantiate it
        config_instance = config()
        return Injector(config_instance)
    else:
        raise TypeError(f"config must be a Config subclass or Config instance, got {type(config)}")
