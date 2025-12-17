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
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from pyiv.chain import ChainHandler, ChainType
from pyiv.config import Config
from pyiv.key import Key
from pyiv.members import InjectorMembersInjector, MembersInjector
from pyiv.optional import get_optional_type, is_optional_type
from pyiv.provider import InjectorProvider, Provider
from pyiv.scope import GlobalSingletonScope, NoScope, Scope, SingletonScope
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
        self._chain_singletons: Dict[Tuple[ChainType, str], ChainHandler] = {}
        self._scoped_instances: Dict[Scope, Dict[Any, Any]] = {}

    def inject(self, cls_or_key: Union[Type, Key[Any]], **kwargs) -> Any:
        """Inject and create an instance of the given class or key.

        Args:
            cls_or_key: The class to instantiate (can be abstract or concrete) or a Key
            **kwargs: Additional keyword arguments to pass to the constructor

        Returns:
            An instance of the class (or registered concrete implementation)

        Raises:
            ValueError: If no registration exists for an abstract class
            TypeError: If the registered concrete is not instantiable
        """
        # Handle Key-based injection
        if isinstance(cls_or_key, Key):
            return self._inject_key(cls_or_key, **kwargs)

        cls = cls_or_key

        # Check for Provider registration
        provider = self._config.get_provider(cls)
        if provider is not None:
            return provider.get()

        # Check for Scope
        scope = self._config.get_scope(cls)
        if scope is not None and not isinstance(scope, NoScope):
            return self._inject_scoped(cls, scope, **kwargs)

        # Fall back to singleton type (backward compatibility)
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

    def _inject_key(self, key: Key[Any], **kwargs) -> Any:
        """Inject using a qualified key.

        Args:
            key: The qualified key
            **kwargs: Additional keyword arguments

        Returns:
            An instance for the key
        """
        binding = self._config.get_key_binding(key)
        if binding is None:
            raise ValueError(f"No binding found for key {key}")

        type_, provider, scope = binding

        # Use provider if available
        if provider is not None:
            if scope is not None:
                # Convert Key to the type expected by scope
                scope_key: Union[Type, str, tuple] = key.type if isinstance(key, Key) else key
                scoped_provider = scope.scope(scope_key, provider)
                return scoped_provider.get()
            return provider.get()

        # Otherwise use standard injection
        if scope is not None:
            return self._inject_scoped(type_, scope, **kwargs)
        return self.inject(type_, **kwargs)

    def _inject_scoped(self, cls: Type, scope: Scope, **kwargs) -> Any:
        """Inject with a specific scope.

        Args:
            cls: The class to inject
            scope: The scope to use
            **kwargs: Additional keyword arguments

        Returns:
            A scoped instance
        """
        # Get or create scope cache
        if scope not in self._scoped_instances:
            self._scoped_instances[scope] = {}

        scope_cache = self._scoped_instances[scope]

        # Check cache
        if cls in scope_cache:
            return scope_cache[cls]

        # Create provider
        provider = InjectorProvider(cls, self)

        # Apply scope - convert cls to Key type for scope
        scope_key: Union[Type, str, tuple] = cls
        scoped_provider = scope.scope(scope_key, provider)

        # Get instance
        instance = scoped_provider.get()

        # Cache if scope supports it (for per-injector scopes)
        if isinstance(scope, (SingletonScope, GlobalSingletonScope)):
            scope_cache[cls] = instance

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

                # Check for Provider[T]
                if self._is_provider_type(annotation):
                    provider_type = self._extract_provider_type(annotation)
                    if provider_type:
                        try:
                            provider = InjectorProvider(provider_type, self)
                            resolved[param_name] = provider
                            continue
                        except (ValueError, TypeError):
                            pass

                # Check for Optional[T]
                if is_optional_type(annotation):
                    optional_type = get_optional_type(annotation)
                    if optional_type:
                        try:
                            resolved[param_name] = self.inject(optional_type)
                            continue
                        except (ValueError, TypeError):
                            # Optional - use None if can't inject
                            resolved[param_name] = None
                            continue

                # Check for Set[T] or List[T] (multibindings)
                origin = get_origin(annotation)
                if origin in (set, Set, list, List):
                    args = get_args(annotation)
                    if args:
                        element_type = args[0]
                        multibinding = self._config.get_multibinding(element_type)
                        if multibinding:
                            set_impls, list_impls, set_instances, list_instances = multibinding
                            if origin in (set, Set):
                                # Create set of instances
                                instances: Set[Any] = set(list_instances)
                                for impl in set_impls:
                                    try:
                                        instances.add(self.inject(impl))
                                    except (ValueError, TypeError):
                                        pass
                                resolved[param_name] = instances
                                continue
                            else:  # list, List
                                # Create list of instances (preserve order)
                                list_instances_result: List[Any] = list(list_instances)
                                for impl in list_impls:
                                    try:
                                        list_instances_result.append(self.inject(impl))
                                    except (ValueError, TypeError):
                                        pass
                                resolved[param_name] = list_instances_result
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

    def inject_chain_handler(self, chain_type: ChainType, handler_type: str) -> ChainHandler:
        """Inject a chain handler instance by handler type.

        Returns the default chain handler implementation for the given handler type.
        Respects singleton configuration.

        Args:
            chain_type: The chain type (e.g., ChainType.ENCODING, ChainType.HASHING)
            handler_type: The handler type identifier (e.g., "json", "md5", "quicksort")

        Returns:
            A chain handler instance

        Raises:
            ValueError: If no chain handler is registered for the handler type

        Example:
            >>> injector = get_injector(MyConfig)
            >>> json_serde = injector.inject_chain_handler(ChainType.ENCODING, "json")
            >>> data = json_serde.serialize({"key": "value"})
        """
        # Check for pre-registered instance
        instance = self._config.get_chain_handler_instance(chain_type, handler_type)
        if instance is not None:
            return instance

        # Get the registered class
        handler_class = self._config.get_chain_handler_registration(chain_type, handler_type)
        if handler_class is None:
            # Get available handler types for this chain type
            available = []
            for (ct, ht), _ in self._config._chain_by_type.items():
                if ct == chain_type:
                    available.append(ht)
            available_str = ", ".join(sorted(available)) or "none"
            raise ValueError(
                f"No chain handler registered for {chain_type.value} type '{handler_type}'. "
                f"Available types: {available_str}"
            )

        # Check singleton configuration
        singleton_type = self._config.get_chain_handler_singleton_type(chain_type, handler_type)

        # Handle global singleton
        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            key = f"chain:{chain_type.value}:{handler_type}"
            instance = GlobalSingletonRegistry.get(key)
            if instance is not None:
                return instance
            # Create new instance
            instance = self._instantiate(handler_class)
            GlobalSingletonRegistry.set(key, instance)
            return instance

        # Check if we have a cached per-injector singleton
        cache_key = (chain_type, handler_type)
        if singleton_type == SingletonType.SINGLETON and cache_key in self._chain_singletons:
            return self._chain_singletons[cache_key]

        # Create instance
        instance = self._instantiate(handler_class)

        # Store as singleton if configured
        if singleton_type == SingletonType.SINGLETON:
            self._chain_singletons[cache_key] = instance

        return instance

    def inject_chain_handler_by_name(self, chain_type: ChainType, name: str) -> ChainHandler:
        """Inject a chain handler instance by name.

        Returns a named chain handler implementation. This allows multiple instances
        of the same handler type with different behaviors (e.g., different
        date formatting, different hash algorithms, etc.).

        Args:
            chain_type: The chain type (e.g., ChainType.ENCODING, ChainType.HASHING)
            name: The handler instance name

        Returns:
            A chain handler instance

        Raises:
            ValueError: If no chain handler is registered with the given name

        Example:
            >>> injector = get_injector(MyConfig)
            >>> input_serde = injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-input")
            >>> output_serde = injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-output")
        """
        # Check for pre-registered instance
        instance = self._config.get_chain_handler_instance(chain_type, name)
        if instance is not None:
            return instance

        # Get the registered class and handler type
        registration = self._config.get_chain_handler_registration_by_name(chain_type, name)
        if registration is None:
            # Get available names for this chain type
            available = []
            for (ct, n), _ in self._config._chain_by_name.items():
                if ct == chain_type:
                    available.append(n)
            for ct, n in self._config._chain_instances.keys():
                if ct == chain_type:
                    available.append(n)
            available_str = ", ".join(sorted(set(available))) or "none"
            raise ValueError(
                f"No chain handler registered with name '{name}' for {chain_type.value}. "
                f"Available names: {available_str}"
            )

        handler_class, handler_type = registration

        # Check singleton configuration
        singleton_type = self._config.get_chain_handler_singleton_type(chain_type, name)

        # Handle global singleton
        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            key = f"chain:{chain_type.value}:{name}"
            instance = GlobalSingletonRegistry.get(key)
            if instance is not None:
                return instance
            # Create new instance
            instance = self._instantiate(handler_class)
            GlobalSingletonRegistry.set(key, instance)
            return instance

        # Check if we have a cached per-injector singleton
        cache_key = (chain_type, name)
        if singleton_type == SingletonType.SINGLETON and cache_key in self._chain_singletons:
            return self._chain_singletons[cache_key]

        # Create instance
        instance = self._instantiate(handler_class)

        # Store as singleton if configured
        if singleton_type == SingletonType.SINGLETON:
            self._chain_singletons[cache_key] = instance

        return instance

    def inject_members(self, instance: Any) -> None:
        """Inject dependencies into an existing instance.

        This method uses MembersInjector to inject dependencies into fields
        and methods of an existing instance. Useful for framework integration
        and legacy code.

        Args:
            instance: The instance to inject dependencies into

        Example:
            >>> from dataclasses import dataclass, field
            >>> @dataclass
            ... class Service:
            ...     db: Database = field(default=None)
            >>>
            >>> service = Service()
            >>> injector.inject_members(service)  # Injects db
        """
        cls = type(instance)
        members_injector = InjectorMembersInjector(cls, self)
        members_injector.inject_members(instance)

    def _is_provider_type(self, annotation: Any) -> bool:
        """Check if annotation is Provider[T].

        Args:
            annotation: The type annotation

        Returns:
            True if it's a Provider type
        """
        origin = get_origin(annotation)
        if origin is None:
            # Check if it's the Provider protocol directly
            try:
                from pyiv.provider import Provider as ProviderProtocol

                if annotation == ProviderProtocol:
                    return True
            except ImportError:
                pass
            return False

        # Check if origin is Provider
        try:
            from pyiv.provider import Provider as ProviderProtocol

            # This is a bit tricky - we need to check if origin matches Provider
            # For now, we'll check the name
            return hasattr(origin, "__name__") and "Provider" in str(origin)
        except ImportError:
            return False

    def _extract_provider_type(self, annotation: Any) -> Optional[Type]:
        """Extract the type parameter from Provider[T].

        Args:
            annotation: The Provider[T] annotation

        Returns:
            The inner type T, or None if not a Provider
        """
        if not self._is_provider_type(annotation):
            return None

        origin = get_origin(annotation)
        if origin is None:
            # It's Provider without type parameter
            return None

        args = get_args(annotation)
        if args:
            return args[0]
        return None


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
