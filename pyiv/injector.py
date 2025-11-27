"""Injector implementation for dependency injection."""

<<<<<<< HEAD
from typing import Any, Dict, Type, Optional, Callable, Union
=======
>>>>>>> origin/main
import inspect
from typing import Any, Callable, Dict, Optional, Type

from pyiv.config import Config
from pyiv.singleton import SingletonType, GlobalSingletonRegistry


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
        # Check singleton type
        singleton_type = self._config.get_singleton_type(cls)
        
        # Handle global singleton
        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            instance = GlobalSingletonRegistry.get(cls)
            if instance is not None:
                return instance
            # Create new instance and store globally
            instance = self._create_instance(cls, **kwargs)
            GlobalSingletonRegistry.set(cls, instance)
            return instance
        
        # Check if we have a registered singleton instance
        instance = self._config.get_instance(cls)
        if instance is not None:
            return instance
<<<<<<< HEAD
        
        # Check if we have a cached per-injector singleton
        if singleton_type == SingletonType.SINGLETON and cls in self._singletons:
=======

        # Check if we have a cached singleton
        if cls in self._singletons:
>>>>>>> origin/main
            return self._singletons[cls]

        # Get the concrete implementation
        concrete = self._config.get_registration(cls)

        if concrete is None:
            # No registration, try to instantiate the class directly
            # (useful for concrete classes that don't need registration)
<<<<<<< HEAD
            instance = self._instantiate(cls, **kwargs)
            # Store as singleton if configured
            if singleton_type == SingletonType.SINGLETON:
                self._singletons[cls] = instance
            return instance
        
        # Check if it's a lazy singleton registration (old style)
=======
            return self._instantiate(cls, **kwargs)

        # Check if it's a singleton registration
>>>>>>> origin/main
        if cls in self._config._instances and self._config._instances[cls] is None:
            # Lazy singleton creation
            instance = self._instantiate(concrete, **kwargs)
            self._singletons[cls] = instance
            self._config._instances[cls] = instance
            return instance

        # Instantiate the concrete implementation
        instance = self._instantiate(concrete, **kwargs)
<<<<<<< HEAD
        
        # Store as singleton if configured
        if singleton_type == SingletonType.SINGLETON:
            self._singletons[cls] = instance
        elif cls in self._config._instances:
            # Old-style singleton caching
=======

        # Cache singleton if configured
        if cls in self._config._instances:
>>>>>>> origin/main
            self._singletons[cls] = instance

        return instance
<<<<<<< HEAD
    
    def _create_instance(self, cls: Type, **kwargs) -> Any:
        """Create an instance, handling registration lookup.
        
        Args:
            cls: The class to instantiate
            **kwargs: Keyword arguments for the constructor
            
        Returns:
            An instance of the class
        """
        concrete = self._config.get_registration(cls)
        if concrete is None:
            return self._instantiate(cls, **kwargs)
        return self._instantiate(concrete, **kwargs)
    
=======

>>>>>>> origin/main
    def _instantiate(self, concrete: Type, **kwargs) -> Any:
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
            if 'injector' in sig.parameters:
                kwargs['injector'] = self
            # Try to inject dependencies from the function signature
            bound_kwargs = self._resolve_dependencies(sig, kwargs)
            return concrete(**bound_kwargs)
        elif isinstance(concrete, type):
            # It's a class
            sig = inspect.signature(concrete.__init__)
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
<<<<<<< HEAD
            
            # Skip varargs and varkwargs - they're handled separately
            if param.kind == inspect.Parameter.VAR_POSITIONAL:  # *args
                continue
            if param.kind == inspect.Parameter.VAR_KEYWORD:  # **kwargs
                continue
            
=======

>>>>>>> origin/main
            # If explicitly provided, use that
            if param_name in provided_kwargs:
                resolved[param_name] = provided_kwargs[param_name]
                continue

            # Check if there's a type annotation
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                
                # Special case: if parameter is named 'injector' and type is Injector, use self
                if param_name == 'injector' and annotation == Injector:
                    resolved[param_name] = self
                    continue
<<<<<<< HEAD
                
                # Only try to inject if it's a registered type (not built-in types)
                # Built-in types like str, int, etc. should use their defaults
                is_builtin = annotation in (str, int, float, bool, bytes, list, dict, tuple, set, frozenset)
                is_registered = not is_builtin and self._config.has_registration(annotation)
                
                if is_registered:
                    # Try to inject this dependency
                    try:
                        resolved[param_name] = self.inject(annotation)
                        continue
                    except (ValueError, TypeError):
                        # Can't inject, will use default if available
                        pass
            
=======
                except (ValueError, TypeError):
                    # Can't inject, will use default if available
                    pass

>>>>>>> origin/main
            # Use default value if available
            if param.default != inspect.Parameter.empty:
                resolved[param_name] = param.default
            elif param_name not in resolved:
                # Required parameter not provided and can't be injected
                raise ValueError(f"Missing required parameter '{param_name}' for {sig}")

        return resolved


<<<<<<< HEAD
def get_injector(config: Union[Type[Config], Config]) -> Injector:
    """Create an injector from a configuration class or instance.
    
    Args:
        config: A Config subclass or Config instance that defines dependencies
        
=======
def get_injector(config_class: Type[Config]) -> Injector:
    """Create an injector from a configuration class.

    Args:
        config_class: A subclass of Config that defines dependencies

>>>>>>> origin/main
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
<<<<<<< HEAD
    if isinstance(config, Config):
        # Already an instance, use it directly
        return Injector(config)
    elif isinstance(config, type) and issubclass(config, Config):
        # It's a class, instantiate it
        config_instance = config()
        return Injector(config_instance)
    else:
        raise TypeError(
            f"config must be a Config subclass or Config instance, got {type(config)}"
        )


=======
    if not issubclass(config_class, Config):
        raise TypeError(f"config_class must be a subclass of Config, got {config_class}")

    config = config_class()
    return Injector(config)
>>>>>>> origin/main
