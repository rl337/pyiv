"""Injector implementation for dependency injection."""

import inspect
from typing import Any, Callable, Dict, Optional, Type, Union

from pyiv.config import Config


class Injector:
    """Dependency injector that creates instances based on configuration."""

    def __init__(self, config: Config):
        """Initialize the injector with a configuration.

        Args:
            config: The configuration object that defines dependencies
        """
        self._config = config
        self._singletons: Dict[Type, Any] = {}

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
        # Check if we have a registered singleton instance
        instance = self._config.get_instance(cls)
        if instance is not None:
            return instance

        # Check if we have a cached singleton
        if cls in self._singletons:
            return self._singletons[cls]

        # Get the concrete implementation
        concrete = self._config.get_registration(cls)

        if concrete is None:
            # No registration, try to instantiate the class directly
            # (useful for concrete classes that don't need registration)
            return self._instantiate(cls, **kwargs)

        # Check if it's a singleton registration
        if cls in self._config._instances and self._config._instances[cls] is None:
            # Lazy singleton creation
            instance = self._instantiate(concrete, **kwargs)
            self._singletons[cls] = instance
            self._config._instances[cls] = instance
            return instance

        # Instantiate the concrete implementation
        instance = self._instantiate(concrete, **kwargs)

        # Cache singleton if configured
        if cls in self._config._instances:
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

    def _resolve_dependencies(self, sig: inspect.Signature, provided_kwargs: Dict[str, Any]) -> Dict[str, Any]:
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

            # If explicitly provided, use that
            if param_name in provided_kwargs:
                resolved[param_name] = provided_kwargs[param_name]
                continue

            # Check if there's a type annotation
            if param.annotation != inspect.Parameter.empty:
                # Try to inject this dependency
                try:
                    resolved[param_name] = self.inject(param.annotation)
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


def get_injector(config_class: Type[Config]) -> Injector:
    """Create an injector from a configuration class.

    Args:
        config_class: A subclass of Config that defines dependencies

    Returns:
        An Injector instance configured with the given config

    Example:
        class MyConfig(Config):
            def configure(self):
                self.register(Database, PostgreSQL)

        injector = get_injector(MyConfig)
        db = injector.inject(Database)
    """
    if not issubclass(config_class, Config):
        raise TypeError(f"config_class must be a subclass of Config, got {config_class}")

    config = config_class()
    return Injector(config)
