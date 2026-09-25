"""Injector implementation for dependency injection.

This module contains the core dependency injection engine. The Injector
class is responsible for creating instances, resolving dependencies,
and managing singleton lifecycles based on configuration.

Architecture:
    - Injector: Main dependency injection engine
    - get_injector(): Factory function for creating injectors from Config
    - Stage: DEVELOPMENT (lazy) vs PRODUCTION (eager singletons)
    - create_child / PrivateConfig: hierarchical environments

The injector uses type annotations and Config registrations to automatically
resolve dependencies. It supports:

- Constructor injection via type annotations
- Singleton lifecycle management
- Factory functions for complex object creation
- Circular dependency detection with path-aware CreationError
- Child injectors and private modules

Usage:
    Create a Config subclass, register dependencies, then create an injector:

    Example:
        >>> from pyiv import Config, Injector, get_injector
        >>> class Database:
        ...     pass
        >>> class PostgreSQL(Database):
        ...     pass
        >>> class Logger:
        ...     pass
        >>> class FileLogger(Logger):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, PostgreSQL)
        ...         self.register(Logger, FileLogger, singleton=True)
        >>> injector = get_injector(MyConfig)
        >>> isinstance(injector.inject(Database), PostgreSQL)
        True
        >>> db = injector.inject(Database)
        >>> logger = injector.inject(Logger)
"""

import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from pyiv.chain import ChainHandler, ChainType
from pyiv.config import Config, PrivateConfig
from pyiv.errors import CreationError, type_name
from pyiv.key import Key
from pyiv.members import InjectorMembersInjector
from pyiv.optional import get_optional_type, is_optional_type
from pyiv.provider import InjectorProvider, Provider
from pyiv.scope import GlobalSingletonScope, NoScope, Scope, SingletonScope
from pyiv.singleton import GlobalSingletonRegistry, SingletonType
from pyiv.stage import Stage

_BUILTIN_TYPES = (
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


class _ChildDelegatingProvider:
    """Provider that resolves a type or key from a child injector."""

    def __init__(self, child: "Injector", target: Union[Type, Key[Any]]):
        self._child = child
        self._target = target

    def get(self) -> Any:
        return self._child.inject(self._target)


class Injector:
    """Resolves types and keys from a :class:`~pyiv.config.Config` graph.

    **Why this exists:** Manual wiring (``new`` / factories everywhere) couples
    construction to call sites. The injector builds objects from bindings and
    constructor annotations so you register once and request by type.

    Example:
        >>> from pyiv import Config, get_injector
        >>> class Database:
        ...     pass
        >>> class PostgreSQL(Database):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, PostgreSQL)
        >>> injector = get_injector(MyConfig)
        >>> isinstance(injector.inject(Database), PostgreSQL)
        True
    """

    def __init__(
        self,
        config: Config,
        *,
        stage: Stage = Stage.DEVELOPMENT,
        parent: Optional["Injector"] = None,
        wire_private: bool = True,
    ):
        """Initialize the injector with a configuration.

        Args:
            config: The configuration object that defines dependencies
            stage: DEVELOPMENT (lazy) or PRODUCTION (eager singletons)
            parent: Optional parent injector for hierarchical lookup
            wire_private: If True, install pending PrivateConfig modules
        """
        self._config = config
        self._stage = stage
        self._parent = parent
        self._singletons: Dict[Type, Any] = {}
        self._chain_singletons: Dict[Tuple[ChainType, str], ChainHandler] = {}
        self._scoped_instances: Dict[Scope, Dict[Any, Any]] = {}
        self._resolving: Set[Any] = set()
        self._path: List[str] = []
        self._children: List["Injector"] = []
        if wire_private:
            self._wire_private_modules()

    @property
    def stage(self) -> Stage:
        """Return the stage this injector was created with."""
        return self._stage

    @property
    def parent(self) -> Optional["Injector"]:
        """Return the parent injector, if any."""
        return self._parent

    def create_child(self, config: Union[Type[Config], Config]) -> "Injector":
        """Create a child injector that inherits parent bindings.

        The child sees parent bindings on miss; the parent cannot see child
        bindings. Singletons created in the child are local to the child.

        Example:
            >>> from pyiv import Config, get_injector
            >>> class Database:
            ...     pass
            >>> class ProdConfig(Config):
            ...     def configure(self):
            ...         self.register(Database, Database)
            >>> class RequestId:
            ...     def __init__(self, value: str = "r1"):
            ...         self.value = value
            >>> class RequestConfig(Config):
            ...     def configure(self):
            ...         self.register(RequestId, RequestId)
            >>> root = get_injector(ProdConfig)
            >>> child = root.create_child(RequestConfig)
            >>> isinstance(child.inject(Database), Database)
            True
            >>> child.inject(RequestId).value
            'r1'
        """
        cfg = config() if isinstance(config, type) else config
        if not isinstance(cfg, Config):
            raise TypeError(f"config must be a Config, got {type(cfg)}")
        child = Injector(cfg, stage=self._stage, parent=self, wire_private=True)
        self._children.append(child)
        return child

    def _wire_private_modules(self) -> None:
        """Wire pending PrivateConfig installs into child environments."""
        pending = list(self._config._pending_private)
        self._config._pending_private.clear()
        for private_cfg in pending:
            child = Injector(private_cfg, stage=self._stage, parent=self, wire_private=True)
            self._children.append(child)
            exposed = private_cfg.get_exposed()
            if not exposed:
                continue
            for item in exposed:
                provider = _ChildDelegatingProvider(child, item)
                if isinstance(item, Key):
                    self._config.register_key(item, provider)
                else:
                    self._config.register_provider(item, provider)

    def inject(self, cls_or_key: Union[Type, Key[Any]], **kwargs) -> Any:
        """Inject and create an instance of the given class or key.

        Args:
            cls_or_key: The class to instantiate (can be abstract or concrete) or a Key
            **kwargs: Additional keyword arguments to pass to the constructor

        Returns:
            An instance of the class (or registered concrete implementation)

        Raises:
            CreationError: If the binding cannot be resolved (with path context)
        """
        identity: Any = cls_or_key
        path_label = type_name(cls_or_key)

        if identity in self._resolving:
            cycle_path = self._path + [path_label]
            raise CreationError(
                f"Circular dependency detected involving {path_label}",
                path=cycle_path,
            )

        self._resolving.add(identity)
        self._path.append(path_label)
        try:
            return self._inject_inner(cls_or_key, **kwargs)
        except CreationError:
            raise
        except Exception as exc:
            raise CreationError(
                str(exc) or type(exc).__name__,
                path=list(self._path),
            ) from exc
        finally:
            self._resolving.discard(identity)
            if self._path:
                self._path.pop()

    def _inject_inner(self, cls_or_key: Union[Type, Key[Any]], **kwargs) -> Any:
        if isinstance(cls_or_key, Key):
            return self._inject_key(cls_or_key, **kwargs)

        cls = cls_or_key

        provider = self._config.get_provider(cls)
        if provider is not None:
            return provider.get()

        if self._config.has_registration(cls) or self._config.get_instance(cls) is not None:
            scope = self._config.get_scope(cls)
            if scope is not None and not isinstance(scope, NoScope):
                return self._inject_scoped(cls, scope, **kwargs)
            return self._create_unscoped(cls, **kwargs)

        # Parent fallback for hierarchical injectors
        if self._parent is not None:
            try:
                return self._parent.inject(cls, **kwargs)
            except CreationError:
                pass

        # JIT for concrete types unless explicit bindings required
        if self._config.requires_explicit_bindings():
            raise CreationError(
                f"No explicit binding for {type_name(cls)} "
                f"(require_explicit_bindings is enabled)",
                path=list(self._path),
            )

        if self._is_concrete_type(cls):
            return self._instantiate(cls, **kwargs)

        raise CreationError(
            f"No binding found for {type_name(cls)}",
            path=list(self._path),
        )

    def _inject_key(self, key: Key[Any], **kwargs) -> Any:
        binding = self._config.get_key_binding(key)
        if binding is None:
            if self._parent is not None:
                return self._parent.inject(key, **kwargs)
            raise CreationError(f"No binding found for key {key}", path=list(self._path))

        type_, provider, scope = binding

        if provider is not None:
            if scope is not None and not isinstance(scope, NoScope):
                scope_key: Union[Type, str, tuple] = key.type if isinstance(key, Key) else key
                scoped_provider = scope.scope(scope_key, provider)
                return scoped_provider.get()
            return provider.get()

        if scope is not None and not isinstance(scope, NoScope):
            return self._inject_scoped(type_, scope, **kwargs)
        return self.inject(type_, **kwargs)

    def _inject_scoped(self, cls: Type, scope: Scope, **kwargs) -> Any:
        if scope not in self._scoped_instances:
            self._scoped_instances[scope] = {}

        scope_cache = self._scoped_instances[scope]

        if cls in scope_cache:
            return scope_cache[cls]

        unscoped = _UnscopedProvider(lambda: self._instantiate_registered(cls, **kwargs))

        scope_key: Union[Type, str, tuple] = cls
        scoped_provider = scope.scope(scope_key, unscoped)
        instance = scoped_provider.get()

        if isinstance(scope, (SingletonScope, GlobalSingletonScope)):
            scope_cache[cls] = instance

        return instance

    def _create_unscoped(self, cls: Type, **kwargs) -> Any:
        singleton_type = self._config.get_singleton_type(cls)

        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            instance = GlobalSingletonRegistry.get(cls)
            if instance is not None:
                return instance
            concrete = self._config.get_registration(cls)
            if concrete is None:
                instance = self._instantiate(cls, **kwargs)
            else:
                instance = self._instantiate(concrete, **kwargs)
            GlobalSingletonRegistry.set(cls, instance)
            return instance

        instance = self._config.get_instance(cls)
        if instance is not None:
            return instance

        if singleton_type == SingletonType.SINGLETON and cls in self._singletons:
            return self._singletons[cls]

        instance = self._instantiate_registered(cls, **kwargs)

        if singleton_type == SingletonType.SINGLETON:
            self._singletons[cls] = instance
        elif cls in self._config._instances:
            self._singletons[cls] = instance

        return instance

    def _instantiate_registered(self, cls: Type, **kwargs) -> Any:
        instance = self._config.get_instance(cls)
        if instance is not None:
            return instance

        concrete = self._config.get_registration(cls)
        if concrete is None:
            return self._instantiate(cls, **kwargs)
        return self._instantiate(concrete, **kwargs)

    def _instantiate(self, concrete: Union[Type, Callable[..., Any]], **kwargs) -> Any:
        if callable(concrete) and not isinstance(concrete, type):
            sig = inspect.signature(concrete)
            if "injector" in sig.parameters:
                kwargs = dict(kwargs)
                kwargs["injector"] = self
            bound_kwargs = self._resolve_dependencies(sig, kwargs)
            return concrete(**bound_kwargs)
        elif isinstance(concrete, type):
            sig = inspect.signature(concrete.__init__)  # type: ignore[misc]
            bound_kwargs = self._resolve_dependencies(sig, kwargs)
            return concrete(**bound_kwargs)
        else:
            raise TypeError(f"Cannot instantiate {concrete}, must be a class or callable")

    def _resolve_dependencies(
        self, sig: inspect.Signature, provided_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        resolved = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                continue
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue

            if param_name in provided_kwargs:
                resolved[param_name] = provided_kwargs[param_name]
                continue

            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation

                if self._is_injector_type(annotation):
                    resolved[param_name] = self
                    continue

                if self._is_provider_type(annotation):
                    provider_type = self._extract_provider_type(annotation)
                    if provider_type:
                        try:
                            provider = InjectorProvider(provider_type, self)
                            resolved[param_name] = provider
                            continue
                        except (ValueError, TypeError, CreationError):
                            pass

                if is_optional_type(annotation):
                    optional_type = get_optional_type(annotation)
                    if optional_type:
                        try:
                            resolved[param_name] = self.inject(optional_type)
                            continue
                        except CreationError:
                            resolved[param_name] = None
                            continue

                origin = get_origin(annotation)
                if origin in (set, Set, list, List):
                    args = get_args(annotation)
                    if args:
                        element_type = args[0]
                        multibinding = self._config.get_multibinding(element_type)
                        if multibinding:
                            set_impls, list_impls, set_instances, list_instances = multibinding
                            if origin in (set, Set):
                                instances: Set[Any] = set(set_instances)
                                for impl in set_impls:
                                    try:
                                        instances.add(self.inject(impl))
                                    except CreationError:
                                        pass
                                resolved[param_name] = instances
                                continue
                            else:
                                list_instances_result: List[Any] = list(list_instances)
                                for impl in list_impls:
                                    try:
                                        list_instances_result.append(self.inject(impl))
                                    except CreationError:
                                        pass
                                resolved[param_name] = list_instances_result
                                continue

                if origin in (dict, Dict, Mapping):
                    args = get_args(annotation)
                    if len(args) == 2:
                        _key_type, value_type = args
                        map_binding = self._config.get_map_multibinding(value_type)
                        if map_binding:
                            impls, map_instances = map_binding
                            result: Dict[Any, Any] = dict(map_instances)
                            for map_key, impl in impls.items():
                                result[map_key] = self.inject(impl)
                            resolved[param_name] = result
                            continue

                is_builtin = annotation in _BUILTIN_TYPES
                if not is_builtin and isinstance(annotation, type):
                    try:
                        resolved[param_name] = self.inject(annotation)
                        continue
                    except CreationError:
                        if param.default != inspect.Parameter.empty:
                            resolved[param_name] = param.default
                            continue
                        raise

            if param.default != inspect.Parameter.empty:
                resolved[param_name] = param.default
            elif param_name not in resolved:
                raise CreationError(
                    f"Missing required parameter '{param_name}' for {sig}",
                    path=list(self._path),
                )

        return resolved

    @staticmethod
    def _is_concrete_type(cls: Type) -> bool:
        if not isinstance(cls, type):
            return False
        if cls in _BUILTIN_TYPES:
            return False
        try:
            return not inspect.isabstract(cls)
        except TypeError:
            return True

    @staticmethod
    def _is_injector_type(annotation: Any) -> bool:
        if annotation is Injector:
            return True
        if isinstance(annotation, type):
            try:
                return issubclass(annotation, Injector)
            except TypeError:
                return False
        return False

    def inject_by_name(self, interface: Type, name: str) -> Type:
        """Inject a specific implementation by name (ReflectionConfig)."""
        if not isinstance(interface, type):
            raise TypeError(f"interface must be a type, got {type(interface)}")

        if not hasattr(self._config, "discover_implementations"):
            raise CreationError(
                f"Config {type(self._config).__name__} does not support reflection-based "
                "discovery. Use ReflectionConfig for inject_by_name() support.",
                path=list(self._path),
            )

        implementations = self._config.discover_implementations(interface)

        if name not in implementations:
            available = ", ".join(sorted(implementations.keys())) or "none"
            raise CreationError(
                f"No implementation '{name}' found for {interface.__name__}. "
                f"Available implementations: {available}",
                path=list(self._path),
            )

        return implementations[name]

    def inject_chain_handler(self, chain_type: ChainType, handler_type: str) -> ChainHandler:
        """Inject a chain handler instance by handler type."""
        instance = self._config.get_chain_handler_instance(chain_type, handler_type)
        if instance is not None:
            return instance

        handler_class = self._config.get_chain_handler_registration(chain_type, handler_type)
        if handler_class is None:
            available = []
            for (ct, ht), _ in self._config._chain_by_type.items():
                if ct == chain_type:
                    available.append(ht)
            available_str = ", ".join(sorted(available)) or "none"
            raise CreationError(
                f"No chain handler registered for {chain_type.value} type '{handler_type}'. "
                f"Available types: {available_str}",
                path=list(self._path),
            )

        singleton_type = self._config.get_chain_handler_singleton_type(chain_type, handler_type)

        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            key = f"chain:{chain_type.value}:{handler_type}"
            instance = GlobalSingletonRegistry.get(key)
            if instance is not None:
                return instance
            instance = self._instantiate(handler_class)
            GlobalSingletonRegistry.set(key, instance)
            return instance

        cache_key = (chain_type, handler_type)
        if singleton_type == SingletonType.SINGLETON and cache_key in self._chain_singletons:
            return self._chain_singletons[cache_key]

        instance = self._instantiate(handler_class)

        if singleton_type == SingletonType.SINGLETON:
            self._chain_singletons[cache_key] = instance

        return instance

    def inject_chain_handler_by_name(self, chain_type: ChainType, name: str) -> ChainHandler:
        """Inject a chain handler instance by name."""
        instance = self._config.get_chain_handler_instance(chain_type, name)
        if instance is not None:
            return instance

        registration = self._config.get_chain_handler_registration_by_name(chain_type, name)
        if registration is None:
            available = []
            for (ct, n), _ in self._config._chain_by_name.items():
                if ct == chain_type:
                    available.append(n)
            for ct, n in self._config._chain_instances.keys():
                if ct == chain_type:
                    available.append(n)
            available_str = ", ".join(sorted(set(available))) or "none"
            raise CreationError(
                f"No chain handler registered with name '{name}' for {chain_type.value}. "
                f"Available names: {available_str}",
                path=list(self._path),
            )

        handler_class, handler_type = registration

        singleton_type = self._config.get_chain_handler_singleton_type(chain_type, name)

        if singleton_type == SingletonType.GLOBAL_SINGLETON:
            key = f"chain:{chain_type.value}:{name}"
            instance = GlobalSingletonRegistry.get(key)
            if instance is not None:
                return instance
            instance = self._instantiate(handler_class)
            GlobalSingletonRegistry.set(key, instance)
            return instance

        cache_key = (chain_type, name)
        if singleton_type == SingletonType.SINGLETON and cache_key in self._chain_singletons:
            return self._chain_singletons[cache_key]

        instance = self._instantiate(handler_class)

        if singleton_type == SingletonType.SINGLETON:
            self._chain_singletons[cache_key] = instance

        return instance

    def inject_members(self, instance: Any) -> None:
        """Inject dependencies into an existing instance."""
        cls = type(instance)
        members_injector = InjectorMembersInjector(cls, self)
        members_injector.inject_members(instance)

    def eager_singletons(self) -> None:
        """Create all singleton-scoped bindings now (used by Stage.PRODUCTION)."""
        errors: List[BaseException] = []
        for abstract in self._config.singleton_bindings():
            try:
                self.inject(abstract)
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise CreationError(
                f"Failed to create {len(errors)} eager singleton(s)",
                causes=errors,
            )

    def _is_provider_type(self, annotation: Any) -> bool:
        origin = get_origin(annotation)
        if origin is None:
            try:
                from pyiv.provider import Provider as ProviderProtocol

                if annotation == ProviderProtocol:
                    return True
            except ImportError:
                pass
            return False

        try:
            return hasattr(origin, "__name__") and "Provider" in str(origin)
        except ImportError:
            return False

    def _extract_provider_type(self, annotation: Any) -> Optional[Type]:
        if not self._is_provider_type(annotation):
            return None

        origin = get_origin(annotation)
        if origin is None:
            return None

        args = get_args(annotation)
        if args:
            return args[0]
        return None


class _UnscopedProvider:
    """Provider that calls a factory once without going through `inject()`."""

    def __init__(self, factory: Callable[[], Any]):
        self._factory = factory

    def get(self) -> Any:
        return self._factory()


def get_injector(
    config: Union[Type[Config], Config],
    *,
    stage: Stage = Stage.DEVELOPMENT,
) -> Injector:
    """Create an injector from a configuration class or instance.

    Args:
        config: A Config subclass or Config instance that defines dependencies
        stage: DEVELOPMENT (default, lazy singletons) or PRODUCTION (eager)

    Returns:
        An Injector instance configured with the given config

    Example:
        >>> from pyiv import Config, get_injector
        >>> class Database:
        ...     pass
        >>> class PostgreSQL(Database):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, PostgreSQL)
        >>> isinstance(get_injector(MyConfig).inject(Database), PostgreSQL)
        True
    """
    if isinstance(config, Config):
        config_instance = config
    elif isinstance(config, type) and issubclass(config, Config):
        config_instance = config()
    else:
        raise TypeError(f"config must be a Config subclass or Config instance, got {type(config)}")

    injector = Injector(config_instance, stage=stage, wire_private=True)
    if stage == Stage.PRODUCTION:
        injector.eager_singletons()
    return injector
