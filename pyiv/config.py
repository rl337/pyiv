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

from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union

from pyiv.binder import Binder, BindingBuilder
from pyiv.chain import ChainHandler, ChainType
from pyiv.key import Key, Qualifier
from pyiv.multibinder import ListMultibinder, Multibinder, SetMultibinder
from pyiv.provider import Provider
from pyiv.scope import NoScope, Scope
from pyiv.singleton import SingletonType

T = TypeVar("T")


class Config:
    """Base class for dependency injection configuration.

    Subclasses should override `configure()` to register dependencies.
    """

    def __init__(self):
        """Initialize the configuration."""
        self._registrations: Dict[Type, Union[Type, Any, Callable]] = {}
        self._instances: Dict[Type, Any] = {}
        self._singleton_types: Dict[Type, SingletonType] = {}
        # Scope registrations: Type -> Scope
        self._scopes: Dict[Type, Scope] = {}
        # Provider registrations: Type -> Provider
        self._providers: Dict[Type, Provider[Any]] = {}
        # Qualified bindings: Key -> (Type, Provider, Scope)
        self._qualified_bindings: Dict[
            Key[Any], Tuple[Type, Optional[Provider[Any]], Optional[Scope]]
        ] = {}
        # Multibindings: Type -> (Set[Type], List[Type], Set[Any], List[Any])
        self._multibindings: Dict[Type, Tuple[Set[Type], List[Type], Set[Any], List[Any]]] = {}
        # Chain handler registrations: (chain_type, handler_type) -> implementation class
        self._chain_by_type: Dict[Tuple[ChainType, str], Type[ChainHandler]] = {}
        # Chain handler registrations: (chain_type, name) -> (implementation class, handler_type)
        self._chain_by_name: Dict[Tuple[ChainType, str], Tuple[Type[ChainHandler], str]] = {}
        # Chain handler instances: (chain_type, name) -> instance (for pre-created instances)
        self._chain_instances: Dict[Tuple[ChainType, str], ChainHandler] = {}
        # Chain handler singleton configuration: (chain_type, name) -> singleton_type
        self._chain_singleton_types: Dict[Tuple[ChainType, str], SingletonType] = {}
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
        scope: Optional[Scope] = None,
        provider: Optional[Provider[Any]] = None,
    ):
        """Register a concrete implementation for an abstract type.

        Args:
            abstract: The abstract class or interface to register
            concrete: The concrete class, instance, or factory function
            singleton: If True, uses SINGLETON type (deprecated, use singleton_type or scope instead)
            singleton_type: Type of singleton behavior (NONE, SINGLETON, or GLOBAL_SINGLETON)
            scope: Scope for lifecycle management (takes precedence over singleton_type)
            provider: Provider to use for instance creation (takes precedence over concrete)

        Raises:
            TypeError: If abstract is not a type
            ValueError: If conflicting parameters are specified
        """
        if not isinstance(abstract, type):
            raise TypeError(f"abstract must be a type, got {type(abstract)}")

        # Handle deprecated singleton parameter
        if singleton and singleton_type != SingletonType.NONE:
            raise ValueError("Cannot specify both singleton=True and singleton_type")
        if singleton:
            singleton_type = SingletonType.SINGLETON

        # Convert singleton_type to scope if scope not provided
        if scope is None and singleton_type != SingletonType.NONE:
            from pyiv.scope import GlobalSingletonScope, SingletonScope

            if singleton_type == SingletonType.GLOBAL_SINGLETON:
                scope = GlobalSingletonScope()
            elif singleton_type == SingletonType.SINGLETON:
                scope = SingletonScope()

        # Store scope
        if scope is not None:
            self._scopes[abstract] = scope

        # Store provider
        if provider is not None:
            self._providers[abstract] = provider
            # Provider takes precedence, but we still store the concrete for reference
            if isinstance(concrete, type):
                self._registrations[abstract] = concrete
            return

        # Store singleton type (for backward compatibility)
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

    def register_chain_handler(
        self,
        chain_type: ChainType,
        handler_type: str,
        handler_class: Type[ChainHandler],
        *,
        singleton_type: SingletonType = SingletonType.SINGLETON,
    ):
        """Register a chain handler implementation for a handler type.

        This registers a default implementation for the handler type.
        When injecting by handler type (without a specific name), this
        implementation will be used.

        Args:
            chain_type: The chain type (e.g., ChainType.ENCODING, ChainType.HASHING)
            handler_type: The handler type identifier (e.g., "json", "md5", "quicksort")
            handler_class: The chain handler implementation class
            singleton_type: Type of singleton behavior (default: SINGLETON)

        Raises:
            TypeError: If handler_class is not a subclass of ChainHandler
            ValueError: If handler_type is empty
        """
        if not isinstance(handler_type, str) or not handler_type:
            raise ValueError(f"handler_type must be a non-empty string, got {handler_type}")
        if not isinstance(handler_class, type) or not issubclass(handler_class, ChainHandler):
            raise TypeError(
                f"handler_class must be a subclass of ChainHandler, got {handler_class}"
            )

        key = (chain_type, handler_type)
        self._chain_by_type[key] = handler_class
        if singleton_type != SingletonType.NONE:
            self._chain_singleton_types[key] = singleton_type

    def register_chain_handler_by_name(
        self,
        chain_type: ChainType,
        name: str,
        handler_class: Type[ChainHandler],
        handler_type: str,
        *,
        singleton_type: SingletonType = SingletonType.SINGLETON,
    ):
        """Register a named chain handler implementation.

        This allows multiple implementations of the same handler type
        with different behaviors (e.g., "json-input", "json-output",
        "md5-fast", "md5-secure").

        Args:
            chain_type: The chain type (e.g., ChainType.ENCODING, ChainType.HASHING)
            name: Unique name for this handler instance
            handler_class: The chain handler implementation class
            handler_type: The handler type identifier (e.g., "json", "md5")
            singleton_type: Type of singleton behavior (default: SINGLETON)

        Raises:
            TypeError: If handler_class is not a subclass of ChainHandler
            ValueError: If name or handler_type is empty
        """
        if not isinstance(name, str) or not name:
            raise ValueError(f"name must be a non-empty string, got {name}")
        if not isinstance(handler_type, str) or not handler_type:
            raise ValueError(f"handler_type must be a non-empty string, got {handler_type}")
        if not isinstance(handler_class, type) or not issubclass(handler_class, ChainHandler):
            raise TypeError(
                f"handler_class must be a subclass of ChainHandler, got {handler_class}"
            )

        key = (chain_type, name)
        self._chain_by_name[key] = (handler_class, handler_type)
        if singleton_type != SingletonType.NONE:
            self._chain_singleton_types[key] = singleton_type

    def register_chain_handler_instance(
        self, chain_type: ChainType, name: str, instance: ChainHandler
    ):
        """Register a pre-created chain handler instance.

        Args:
            chain_type: The chain type
            name: Unique name for this handler instance
            instance: The pre-created chain handler instance

        Raises:
            TypeError: If instance is not a ChainHandler
            ValueError: If name is empty
        """
        if not isinstance(name, str) or not name:
            raise ValueError(f"name must be a non-empty string, got {name}")
        if not isinstance(instance, ChainHandler):
            raise TypeError(f"instance must be a ChainHandler, got {type(instance)}")

        key = (chain_type, name)
        self._chain_instances[key] = instance
        # Also register by handler type if not already registered
        handler_type = instance.handler_type
        type_key = (chain_type, handler_type)
        if type_key not in self._chain_by_type:
            self._chain_by_type[type_key] = type(instance)

    def get_chain_handler_registration(
        self, chain_type: ChainType, handler_type: str
    ) -> Optional[Type[ChainHandler]]:
        """Get the registered chain handler class for a handler type.

        Args:
            chain_type: The chain type
            handler_type: The handler type identifier

        Returns:
            The registered chain handler class, or None if not found
        """
        return self._chain_by_type.get((chain_type, handler_type))

    def get_chain_handler_registration_by_name(
        self, chain_type: ChainType, name: str
    ) -> Optional[Tuple[Type[ChainHandler], str]]:
        """Get the registered chain handler class and handler type for a name.

        Args:
            chain_type: The chain type
            name: The handler instance name

        Returns:
            A tuple of (handler class, handler_type), or None if not found
        """
        return self._chain_by_name.get((chain_type, name))

    def get_chain_handler_instance(
        self, chain_type: ChainType, name: str
    ) -> Optional[ChainHandler]:
        """Get a pre-registered chain handler instance.

        Args:
            chain_type: The chain type
            name: The handler instance name

        Returns:
            The chain handler instance, or None if not found
        """
        return self._chain_instances.get((chain_type, name))

    def has_chain_handler_registration(self, chain_type: ChainType, handler_type: str) -> bool:
        """Check if a chain handler is registered for a handler type.

        Args:
            chain_type: The chain type
            handler_type: The handler type identifier

        Returns:
            True if registered, False otherwise
        """
        return (chain_type, handler_type) in self._chain_by_type

    def has_chain_handler_registration_by_name(self, chain_type: ChainType, name: str) -> bool:
        """Check if a chain handler is registered by name.

        Args:
            chain_type: The chain type
            name: The handler instance name

        Returns:
            True if registered, False otherwise
        """
        key = (chain_type, name)
        return key in self._chain_by_name or key in self._chain_instances

    def get_chain_handler_singleton_type(self, chain_type: ChainType, name: str) -> SingletonType:
        """Get the singleton type for a chain handler registration.

        Args:
            chain_type: The chain type
            name: The handler instance name or handler type

        Returns:
            The singleton type, or SingletonType.NONE if not registered or not a singleton
        """
        key = (chain_type, name)
        return self._chain_singleton_types.get(key, SingletonType.NONE)

    def get_scope(self, abstract: Type) -> Optional[Scope]:
        """Get the scope for a registered type.

        Args:
            abstract: The abstract class or interface

        Returns:
            The scope, or None if not registered or no scope
        """
        return self._scopes.get(abstract)

    def get_provider(self, abstract: Type) -> Optional[Provider[Any]]:
        """Get the provider for a registered type.

        Args:
            abstract: The abstract class or interface

        Returns:
            The provider, or None if not registered or no provider
        """
        return self._providers.get(abstract)

    def register_provider(self, abstract: Type, provider: Provider[Any]) -> None:
        """Register a provider for a type.

        Args:
            abstract: The abstract class or interface
            provider: The provider to use for instance creation
        """
        if not isinstance(abstract, type):
            raise TypeError(f"abstract must be a type, got {type(abstract)}")
        self._providers[abstract] = provider

    def register_key(
        self,
        key: Key[Any],
        implementation: Union[Type, Provider[Any]],
        *,
        scope: Optional[Scope] = None,
    ) -> None:
        """Register a qualified binding using a Key.

        Args:
            key: The qualified key
            implementation: The implementation class or provider
            scope: Optional scope for lifecycle management
        """
        provider: Optional[Provider[Any]] = None
        # Check if it has a get method (Provider protocol)
        if hasattr(implementation, "get") and callable(getattr(implementation, "get")):
            provider = implementation  # type: ignore[assignment]
        self._qualified_bindings[key] = (key.type, provider, scope)

    def get_key_binding(
        self, key: Key[Any]
    ) -> Optional[Tuple[Type, Optional[Provider[Any]], Optional[Scope]]]:
        """Get a qualified binding for a key.

        Args:
            key: The qualified key

        Returns:
            Tuple of (type, provider, scope) or None if not found
        """
        return self._qualified_bindings.get(key)

    def multibinder(self, interface: Type[T], as_set: bool = True) -> Multibinder[T]:
        """Create a multibinder for multiple implementations.

        Args:
            interface: The interface type
            as_set: If True, creates SetMultibinder, else ListMultibinder

        Returns:
            A multibinder instance
        """
        if as_set:
            return SetMultibinder(interface, self)
        else:
            return ListMultibinder(interface, self)

    def register_multibinding(
        self,
        interface: Type[T],
        implementation: Type[T],
        *,
        as_set: bool = True,
    ) -> None:
        """Register an implementation in a multibinding.

        Args:
            interface: The interface type
            implementation: The implementation class
            as_set: If True, adds to set, else to list
        """
        if interface not in self._multibindings:
            self._multibindings[interface] = (set(), [], set(), [])
        set_impls, list_impls, set_instances, list_instances = self._multibindings[interface]
        if as_set:
            set_impls.add(implementation)
        else:
            list_impls.append(implementation)

    def get_multibinding(
        self, interface: Type[T]
    ) -> Optional[Tuple[Set[Type], List[Type], Set[Any], List[Any]]]:
        """Get multibinding implementations for an interface.

        Args:
            interface: The interface type

        Returns:
            Tuple of (set_impls, list_impls, set_instances, list_instances) or None
        """
        return self._multibindings.get(interface)

    def get_binder(self) -> Binder:
        """Get a binder for fluent configuration.

        Returns:
            A binder instance
        """
        from pyiv.binder_impl import ConfigBinder

        return ConfigBinder(self)
