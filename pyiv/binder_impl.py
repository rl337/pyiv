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
from pyiv.version import (
    PEP440,
    PYTHON_VERSION_DOMAIN,
    PackageVersionSource,
    PythonVersionSource,
    VersionBindingCandidate,
    package_version_domain,
)

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
        self._version_conditioned = False
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
        if self._version_conditioned:
            # Scope is stored on the candidate; patch the last candidate for
            # this abstract/domain/specifier if present.
            self._patch_last_candidate_scope(scope)
        else:
            self._config._scopes[self._abstract] = scope
        return self

    def for_version(
        self,
        domain: str,
        specifier: str,
        *,
        parser: Optional[str] = None,
    ) -> "ConfigBindingBuilder[T]":
        """Restrict this binding to a named version domain + specifier."""
        self._ensure_target()
        self._retract_unconditional()
        candidate = VersionBindingCandidate(
            abstract=self._abstract,
            domain=domain,
            specifier=specifier,
            implementation=self._implementation,
            instance=self._instance,
            provider=self._provider,
            scope=self._scope,
            parser_name=parser,
        )
        self._config.add_version_candidate(candidate)
        self._version_conditioned = True
        self._finalized = True
        return self

    def for_package_version(
        self,
        distribution: str,
        specifier: str,
    ) -> "ConfigBindingBuilder[T]":
        """Restrict this binding to an installed distribution version."""
        domain = package_version_domain(distribution)
        if domain not in self._config._version_sources:
            self._config.register_version_source(domain, PackageVersionSource(distribution))
        if domain not in self._config._version_domain_parsers:
            self._config.use_version_parser(domain, PEP440)
        return self.for_version(domain, specifier, parser=PEP440)

    def for_python_version(self, specifier: str) -> "ConfigBindingBuilder[T]":
        """Restrict this binding to the running interpreter version."""
        domain = PYTHON_VERSION_DOMAIN
        # Do not eagerly bind SysPythonVersionProvider here: an override
        # module's for_python_version would otherwise last-wins wipe a base
        # FixedPythonVersionProvider on merge. PythonVersionSource falls back
        # to Sys; apply_version_selection ensures an injectable binding later.
        if domain not in self._config._version_sources:
            self._config.register_version_source(domain, PythonVersionSource(config=self._config))
        if domain not in self._config._version_domain_parsers:
            self._config.use_version_parser(domain, PEP440)
        return self.for_version(domain, specifier, parser=PEP440)

    def _ensure_target(self) -> None:
        if self._implementation is None and self._instance is None and self._provider is None:
            raise ValueError(
                "for_version* requires .to(...), .to_instance(...), or "
                ".to_provider(...) before the version condition"
            )

    def _retract_unconditional(self) -> None:
        """Remove the unconditional registration written by ``_finalize``."""
        abstract = self._abstract
        if self._provider is not None:
            if self._config._providers.get(abstract) is self._provider:
                del self._config._providers[abstract]
        if self._instance is not None:
            if self._config._instances.get(abstract) is self._instance:
                del self._config._instances[abstract]
        if self._implementation is not None:
            if self._config._registrations.get(abstract) is self._implementation:
                del self._config._registrations[abstract]
        # Drop self-binding left from __init__ when converting early.
        if (
            self._implementation is None
            and self._instance is None
            and self._provider is None
            and self._config._registrations.get(abstract) is abstract
        ):
            del self._config._registrations[abstract]
        # Scope stays only if an unconditional binding remains; otherwise clear
        # the scope entry written for this builder so fallbacks are clean.
        if abstract not in self._config._registrations and abstract not in self._config._providers:
            if abstract in self._config._scopes and self._scope is not None:
                if self._config._scopes.get(abstract) is self._scope:
                    del self._config._scopes[abstract]
            if abstract in self._config._instances and self._config._instances[abstract] is None:
                del self._config._instances[abstract]

    def _patch_last_candidate_scope(self, scope: Scope) -> None:
        candidates = self._config._version_candidates
        for i in range(len(candidates) - 1, -1, -1):
            c = candidates[i]
            if c.abstract is self._abstract:
                candidates[i] = VersionBindingCandidate(
                    abstract=c.abstract,
                    domain=c.domain,
                    specifier=c.specifier,
                    implementation=c.implementation,
                    instance=c.instance,
                    provider=c.provider,
                    scope=scope,
                    parser_name=c.parser_name,
                )
                return

    def _finalize(self) -> None:
        """Finalize the binding registration."""
        if self._finalized or self._version_conditioned:
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

    def for_version(
        self,
        domain: str,
        specifier: str,
        *,
        parser: Optional[str] = None,
    ) -> "ConfigKeyBindingBuilder[T]":
        raise NotImplementedError(
            "Version-conditioned bindings are not yet supported on bind_key; "
            "use bind(Type).for_version(...) for unqualified types"
        )

    def for_package_version(
        self, distribution: str, specifier: str
    ) -> "ConfigKeyBindingBuilder[T]":
        raise NotImplementedError(
            "Version-conditioned bindings are not yet supported on bind_key; "
            "use bind(Type).for_package_version(...) for unqualified types"
        )

    def for_python_version(self, specifier: str) -> "ConfigKeyBindingBuilder[T]":
        raise NotImplementedError(
            "Version-conditioned bindings are not yet supported on bind_key; "
            "use bind(Type).for_python_version(...) for unqualified types"
        )

    def _finalize(self) -> None:
        if self._finalized:
            return

        if self._instance is not None:
            self._config.register_key(
                self._key, InstanceProvider(self._instance), scope=self._scope, replace=True
            )
        elif self._provider is not None:
            self._config.register_key(self._key, self._provider, scope=self._scope, replace=True)
        elif self._implementation is not None:
            self._config.register_key(
                self._key, self._implementation, scope=self._scope, replace=True
            )
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

    def version_source(self, domain: str, source: Any) -> None:
        """Register a VersionSource for a named domain."""
        self._config.register_version_source(domain, source)

    def version_parser(self, name: str, parser: Any) -> None:
        """Register a named VersionParser (e.g. custom OS-release grammar)."""
        self._config.register_version_parser(name, parser)

    def use_version_parser(self, domain: str, parser_name: str) -> None:
        """Point a version domain at a named VersionParser."""
        self._config.use_version_parser(domain, parser_name)

    def finalize(self) -> None:
        """Finalize all pending bindings."""
        for builder in self._builders:
            builder._finalize()
        self._builders.clear()
