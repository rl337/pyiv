"""Concrete Binder implementation for Config.

This module provides the ConfigBinder implementation that works with Config
to provide a fluent configuration API.
"""

from typing import Any, List, Optional, Type, TypeVar, Union

from pyiv.binder import Binder, BindingBuilder
from pyiv.config import Config
from pyiv.key import Key
from pyiv.provider import InstanceProvider, Provider
from pyiv.scope import NoScope, Scope

T = TypeVar("T")


class ConfigBindingBuilder(BindingBuilder[T]):
    """Binding builder implementation for Config."""

    def __init__(self, config: Config, abstract: Type[T]):
        """Initialize binding builder.

        Args:
            config: The config to register bindings with
            abstract: The abstract type being bound
        """
        self._config = config
        self._abstract = abstract
        self._implementation: Optional[Type[T]] = None
        self._instance: Optional[T] = None
        self._provider: Optional[Provider[T]] = None
        self._scope: Optional[Scope] = None
        self._finalized = False
        # Untargeted self-binding; replaced by to / to_instance / to_provider.
        self._config.register(self._abstract, self._abstract)

    def to(self, implementation: Type[T]) -> "ConfigBindingBuilder[T]":
        """Bind to a concrete implementation."""
        self._implementation = implementation
        self._instance = None
        self._provider = None
        self._finalized = False
        self._finalize()
        return self

    def to_instance(self, instance: T) -> "ConfigBindingBuilder[T]":
        """Bind to a pre-created instance."""
        self._instance = instance
        self._implementation = None
        self._provider = None
        self._finalized = False
        self._finalize()
        return self

    def to_provider(self, provider: Provider[T]) -> "ConfigBindingBuilder[T]":
        """Bind to a provider."""
        self._provider = provider
        self._implementation = None
        self._instance = None
        self._finalized = False
        self._finalize()
        return self

    def in_scope(self, scope: Scope) -> "ConfigBindingBuilder[T]":
        """Set the scope for this binding."""
        self._scope = scope
        self._config._scopes[self._abstract] = scope
        return self

    def _finalize(self) -> None:
        """Finalize the binding registration."""
        if self._finalized:
            return

        if self._instance is not None:
            self._config.register_instance(self._abstract, self._instance)
            if self._scope is not None:
                self._config._scopes[self._abstract] = self._scope
        elif self._provider is not None:
            self._config.register_provider(self._abstract, self._provider)
            if self._scope is not None:
                self._config._scopes[self._abstract] = self._scope
        elif self._implementation is not None:
            self._config.register(
                self._abstract,
                self._implementation,
                scope=self._scope if self._scope is not None else NoScope(),
            )
        else:
            # Untargeted: already registered abstract -> abstract in __init__
            if self._scope is not None:
                self._config._scopes[self._abstract] = self._scope

        self._finalized = True


class ConfigKeyBindingBuilder(BindingBuilder[T]):
    """Binding builder for qualified keys."""

    def __init__(self, config: Config, key: Key[T]):
        self._config = config
        self._key = key
        self._implementation: Optional[Type[T]] = None
        self._instance: Optional[T] = None
        self._provider: Optional[Provider[T]] = None
        self._scope: Optional[Scope] = None
        self._finalized = False

    def to(self, implementation: Type[T]) -> "ConfigKeyBindingBuilder[T]":
        self._implementation = implementation
        self._instance = None
        self._provider = None
        self._finalized = False
        self._finalize()
        return self

    def to_instance(self, instance: T) -> "ConfigKeyBindingBuilder[T]":
        self._instance = instance
        self._implementation = None
        self._provider = None
        self._finalized = False
        self._finalize()
        return self

    def to_provider(self, provider: Provider[T]) -> "ConfigKeyBindingBuilder[T]":
        self._provider = provider
        self._implementation = None
        self._instance = None
        self._finalized = False
        self._finalize()
        return self

    def in_scope(self, scope: Scope) -> "ConfigKeyBindingBuilder[T]":
        self._scope = scope
        if self._finalized:
            binding = self._config.get_key_binding(self._key)
            if binding is not None:
                type_, provider, _ = binding
                self._config._qualified_bindings[self._key] = (type_, provider, scope)
        return self

    def _finalize(self) -> None:
        if self._finalized:
            return

        if self._instance is not None:
            self._config.register_key(
                self._key, InstanceProvider(self._instance), scope=self._scope
            )
        elif self._provider is not None:
            self._config.register_key(self._key, self._provider, scope=self._scope)
        elif self._implementation is not None:
            self._config.register_key(self._key, self._implementation, scope=self._scope)
        else:
            return

        self._finalized = True


class ConfigBinder(Binder):
    """Concrete Binder implementation for Config."""

    def __init__(self, config: Config):
        self._config = config
        self._builders: List[Union[ConfigBindingBuilder[Any], ConfigKeyBindingBuilder[Any]]] = []

    def bind(self, abstract: Type[T]) -> BindingBuilder[T]:
        builder = ConfigBindingBuilder(self._config, abstract)
        self._builders.append(builder)
        return builder

    def bind_key(self, key: Key[T]) -> BindingBuilder[T]:
        builder: ConfigKeyBindingBuilder[Any] = ConfigKeyBindingBuilder(self._config, key)
        self._builders.append(builder)
        return builder

    def bind_instance(self, abstract: Type[T], instance: T) -> None:
        self._config.register_instance(abstract, instance)

    def install(self, config: Any) -> None:
        """Install another configuration module into this config.

        Later installs overwrite earlier bindings for the same type or key
        (last wins). Use :func:`pyiv.override.override` when you need an
        explicit base/override overlay for tests.

        PrivateConfig installs are deferred until injector construction so
        exposed bindings can delegate into an isolated child environment.
        """
        self._config.install(config)

    def expose(self, type_or_key: Union[Type[Any], Key[Any]]) -> None:
        """Expose a binding from a PrivateConfig to the parent environment."""
        self._config.expose(type_or_key)

    def require_explicit_bindings(self) -> None:
        """Disable just-in-time construction of unregistered concrete types."""
        self._config.require_explicit_bindings()

    def finalize(self) -> None:
        """Finalize all pending bindings."""
        for builder in self._builders:
            builder._finalize()
        self._builders.clear()
