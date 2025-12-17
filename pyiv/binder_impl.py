"""Concrete Binder implementation for Config.

This module provides the ConfigBinder implementation that works with Config
to provide a fluent configuration API.
"""

from typing import Any, Generic, List, Optional, Type, TypeVar

from pyiv.binder import Binder, BindingBuilder
from pyiv.config import Config
from pyiv.key import Key
from pyiv.provider import InjectorProvider, InstanceProvider, Provider
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

    def to(self, implementation: Type[T]) -> "ConfigBindingBuilder[T]":
        """Bind to a concrete implementation.

        Args:
            implementation: The concrete class to bind to

        Returns:
            Self for method chaining
        """
        self._implementation = implementation
        self._finalize()
        return self

    def to_instance(self, instance: T) -> "ConfigBindingBuilder[T]":
        """Bind to a pre-created instance.

        Args:
            instance: The instance to bind to

        Returns:
            Self for method chaining
        """
        self._instance = instance
        self._finalize()
        return self

    def to_provider(self, provider: Provider[T]) -> "ConfigBindingBuilder[T]":
        """Bind to a provider.

        Args:
            provider: The provider to use for instance creation

        Returns:
            Self for method chaining
        """
        self._provider = provider
        self._finalize()
        return self

    def in_scope(self, scope: Scope) -> "ConfigBindingBuilder[T]":
        """Set the scope for this binding.

        Args:
            scope: The scope to use

        Returns:
            Self for method chaining
        """
        self._scope = scope
        # Update scope if already finalized
        if hasattr(self, "_finalized") and getattr(self, "_finalized", False):
            self._config._scopes[self._abstract] = scope
        return self

    def _finalize(self) -> None:
        """Finalize the binding registration."""
        if hasattr(self, "_finalized") and getattr(self, "_finalized", False):
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
            # Don't raise error - allow chaining
            return

        self._finalized = True


class ConfigBinder(Binder):
    """Concrete Binder implementation for Config."""

    def __init__(self, config: Config):
        """Initialize binder.

        Args:
            config: The config to register bindings with
        """
        self._config = config
        self._builders: List[ConfigBindingBuilder[Any]] = []

    def bind(self, abstract: Type[T]) -> BindingBuilder[T]:
        """Start a binding configuration.

        Args:
            abstract: The abstract type to bind

        Returns:
            A binding builder for fluent configuration
        """
        builder = ConfigBindingBuilder(self._config, abstract)
        self._builders.append(builder)
        return builder

    def bind_key(self, key: Key[T]) -> BindingBuilder[T]:
        """Start a binding configuration with a qualified key.

        Args:
            key: The qualified key to bind

        Returns:
            A binding builder for fluent configuration
        """
        # For qualified keys, we need a special builder
        builder: ConfigBindingBuilder[Any] = ConfigBindingBuilder(self._config, key.type)  # type: ignore[arg-type]
        builder._key = key  # type: ignore[attr-defined]  # Store the key
        self._builders.append(builder)
        return builder

    def bind_instance(self, abstract: Type[T], instance: T) -> None:
        """Bind to a pre-created instance.

        Args:
            abstract: The abstract type
            instance: The pre-created instance
        """
        self._config.register_instance(abstract, instance)

    def install(self, config: Any) -> None:
        """Install another configuration module.

        Args:
            config: Another Config instance to install
        """
        # This would require merging configs, which is complex
        # For now, we'll raise NotImplementedError
        raise NotImplementedError("Config installation not yet implemented")

    def finalize(self) -> None:
        """Finalize all pending bindings."""
        for builder in self._builders:
            builder._finalize()
        self._builders.clear()
