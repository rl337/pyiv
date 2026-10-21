"""Binder interface for fluent configuration API.

This module provides the Binder interface for configuring dependency bindings
in a fluent, decoupled way. The Binder separates the configuration API from
the implementation, making Config more testable and enabling programmatic
configuration.

**What Problem Does This Solve?**

Binders solve the configuration API design problem:

- **Fluent API**: Method chaining for readable, expressive configuration
- **Separation of Concerns**: Configuration API separated from implementation
- **Testability**: Mock binders for testing configuration logic
- **Programmatic Configuration**: Build configurations dynamically
- **Better Readability**: ``binder.bind(X).to(Y).in_scope(Z)`` is clearer than nested calls
- **Version conditions**: ``.for_version`` / ``.for_package_version`` /
  ``.for_package_present`` / ``.for_package_absent`` / ``.for_python_version``
  select among implementations from named version domains (see :mod:`pyiv.version`)

**Real-World Use Cases:**

- **Dynamic Configuration**: Build configurations based on environment variables
- **Configuration Testing**: Mock binders to test configuration logic
- **Modular Configuration**: Compose configurations from multiple sources
- **Framework Integration**: Provide fluent APIs for framework-specific configuration
- **Environment adapters**: Bind different implementations for Python or
  package versions, or optional accelerators via ``for_package_present`` /
  ``for_package_absent``

Architecture:
    - Binder: Protocol defining the binder interface
    - BindingBuilder: Fluent builder for configuring bindings
    - ConfigBinder: Concrete binder implementation used by Config

Usage Examples:

    Basic Fluent Configuration:
        >>> from pyiv.binder import Binder
        >>> from pyiv.scope import SingletonScope
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Database:
        ...     pass
        >>>
        >>> class PostgreSQL(Database):
        ...     pass
        >>>
        >>> class Logger:
        ...     pass
        >>>
        >>> class FileLogger(Logger):
        ...     pass
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         binder = self.get_binder()
        ...         # Fluent API - easy to read and chain
        ...         binder.bind(Database).to(PostgreSQL)
        ...         binder.bind(Logger).to(FileLogger).in_scope(SingletonScope())
        >>>
        >>> injector = get_injector(MyConfig)
        >>> db = injector.inject(Database)
        >>> isinstance(db, PostgreSQL)
        True

    Binding to Instances:
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Cache:
        ...     def __init__(self):
        ...         self.data = {}
        >>>
        >>> cache = Cache()
        >>> class InstanceConfig(Config):
        ...     def configure(self):
        ...         self.get_binder().bind_instance(Cache, cache)
        >>>
        >>> injector = get_injector(InstanceConfig)
        >>> injector.inject(Cache) is cache
        True

    Optional package present / absent (see :mod:`pyiv.version`):
        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import MapVersionSource, package_version_domain
        >>> class Encoder:
        ...     kind = "base"
        >>> class Fast(Encoder):
        ...     kind = "fast"
        >>> class Std(Encoder):
        ...     kind = "std"
        >>> domain = package_version_domain("orjson")
        >>> class AccelConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         b.version_source(domain, MapVersionSource({domain: "3.0.0"}))
        ...         b.bind(Encoder).to(Fast).for_package_present("orjson")
        ...         b.bind(Encoder).to(Std).for_package_absent("orjson")
        >>> get_injector(AccelConfig).inject(Encoder).kind
        'fast'
"""

from typing import Any, Generic, Protocol, Type, TypeVar

from pyiv.key import Key
from pyiv.provider import Provider
from pyiv.scope import Scope

T = TypeVar("T")


class BindingBuilder(Protocol, Generic[T]):
    """Fluent steps after :meth:`Binder.bind` (``.to`` / ``.in_scope`` / ``.for_version`` / …).

    **Why this exists:** A single ``register(...)`` call buries scope,
    provider, and version-condition choices in kwargs. The builder makes the
    binding shape readable as a chain while still writing the same ``Config``
    store (or a version-candidate list).

    Example:
        >>> from pyiv import Config, get_injector
        >>> from pyiv.scope import SingletonScope
        >>> class Database:
        ...     pass
        >>> class PostgreSQL(Database):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.get_binder().bind(Database).to(PostgreSQL).in_scope(SingletonScope())
        >>> isinstance(get_injector(MyConfig).inject(Database), PostgreSQL)
        True

    Version condition (see :mod:`pyiv.version` for full examples)::

        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import FixedPythonVersionProvider, PythonVersionProvider
        >>> class Api:
        ...     tag = "base"
        >>> class V1(Api):
        ...     tag = "v1"
        >>> class V2(Api):
        ...     tag = "v2"
        >>> class ApiConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         b.bind(PythonVersionProvider).to_instance(
        ...             FixedPythonVersionProvider("3.12.0")
        ...         )
        ...         b.bind(Api).to(V1).for_python_version("<3.11")
        ...         b.bind(Api).to(V2).for_python_version(">=3.11")
        >>> get_injector(ApiConfig).inject(Api).tag
        'v2'

    Package present / absent (optional accelerator)::

        >>> from pyiv import Config, get_injector
        >>> class Encoder:
        ...     kind = "base"
        >>> class Fast(Encoder):
        ...     kind = "fast"
        >>> class Std(Encoder):
        ...     kind = "std"
        >>> class MissingAccelConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         missing = "pyiv-definitely-not-installed-xyz"
        ...         b.bind(Encoder).to(Fast).for_package_present(missing)
        ...         b.bind(Encoder).to(Std).for_package_absent(missing)
        >>> get_injector(MissingAccelConfig).inject(Encoder).kind
        'std'
    """

    def to(self, implementation: Type[T]) -> "BindingBuilder[T]":
        """Bind to a concrete implementation.

        Args:
            implementation: The concrete class to bind to

        Returns:
            Self for method chaining
        """
        ...

    def to_instance(self, instance: T) -> "BindingBuilder[T]":
        """Bind to a pre-created instance.

        Args:
            instance: The instance to bind to

        Returns:
            Self for method chaining
        """
        ...

    def to_provider(self, provider: Provider[T]) -> "BindingBuilder[T]":
        """Bind to a provider.

        Args:
            provider: The provider to use for instance creation

        Returns:
            Self for method chaining
        """
        ...

    def in_scope(self, scope: Scope) -> "BindingBuilder[T]":
        """Set the scope for this binding.

        Args:
            scope: The scope to use

        Returns:
            Self for method chaining
        """
        ...

    def for_version(
        self,
        domain: str,
        specifier: str,
        *,
        parser: Any = None,
    ) -> "BindingBuilder[T]":
        """Restrict this binding to a named version domain + specifier.

        Registers a version **candidate** instead of an unconditional binding.
        Prefer :meth:`for_python_version`, :meth:`for_package_version`,
        :meth:`for_package_present`, or :meth:`for_package_absent` when those
        cover the domain. See :mod:`pyiv.version` and the version-bindings
        guide.

        Args:
            domain: Named version domain (must have a :class:`~pyiv.version.VersionSource`)
            specifier: Domain-specific version constraint string (or
                :data:`~pyiv.version.PACKAGE_PRESENT` /
                :data:`~pyiv.version.PACKAGE_ABSENT` for package domains)
            parser: Optional named :class:`~pyiv.version.VersionParser`
                (defaults to the domain's parser, then ``\"PEP440\"``)

        Returns:
            Self for method chaining
        """
        ...

    def for_package_version(
        self,
        distribution: str,
        specifier: str,
    ) -> "BindingBuilder[T]":
        """Restrict this binding to an installed distribution's PEP 440 version.

        Convenience for ``for_version`` with
        :class:`~pyiv.version.PackageVersionSource` and the built-in
        ``\"PEP440\"`` :class:`~pyiv.pep440.Pep440VersionParser`.

        Pass :data:`~pyiv.version.PACKAGE_PRESENT` (``\"*\"``) /
        :data:`~pyiv.version.PACKAGE_ABSENT` (``\"!\"``) — or use
        :meth:`for_package_present` / :meth:`for_package_absent`.

        Example:
            >>> from pyiv import Config, get_injector
            >>> from pyiv.version import MapVersionSource, package_version_domain
            >>> class HttpClient:
            ...     name = "base"
            >>> class Legacy(HttpClient):
            ...     name = "legacy"
            >>> class Modern(HttpClient):
            ...     name = "modern"
            >>> domain = package_version_domain("requests")
            >>> class HttpConfig(Config):
            ...     def configure(self):
            ...         b = self.get_binder()
            ...         b.version_source(domain, MapVersionSource({domain: "2.31.0"}))
            ...         b.bind(HttpClient).to(Legacy).for_package_version(
            ...             "requests", "<2.30"
            ...         )
            ...         b.bind(HttpClient).to(Modern).for_package_version(
            ...             "requests", ">=2.30,<3"
            ...         )
            >>> get_injector(HttpConfig).inject(HttpClient).name
            'modern'

        Args:
            distribution: Distribution name (``importlib.metadata``), not
                necessarily the import package name
            specifier: PEP 440 version specifier, or ``\"*\"`` / ``\"!\"`` for
                presence / absence

        Returns:
            Self for method chaining
        """
        ...

    def for_package_present(self, distribution: str) -> "BindingBuilder[T]":
        """Restrict this binding to when the distribution is installed.

        Sugar for ``for_package_version(distribution, \"*\")``. Matches any
        installed version; when the distribution is absent the candidate does
        not match — pair with :meth:`for_package_absent` or an unconditional
        fallback registered after.

        Pass the **distribution** name (as on PyPI / ``importlib.metadata``),
        which may differ from the import package name.

        Example:
            >>> from pyiv import Config, get_injector
            >>> from pyiv.version import MapVersionSource, package_version_domain
            >>> class Encoder:
            ...     kind = "base"
            >>> class FastEncoder(Encoder):
            ...     kind = "fast"
            >>> class StdEncoder(Encoder):
            ...     kind = "std"
            >>> domain = package_version_domain("cjson")
            >>> class EncoderConfig(Config):
            ...     def configure(self):
            ...         b = self.get_binder()
            ...         # Simulate an installed optional accelerator in tests.
            ...         b.version_source(domain, MapVersionSource({domain: "1.0.0"}))
            ...         b.bind(Encoder).to(FastEncoder).for_package_present("cjson")
            ...         b.bind(Encoder).to(StdEncoder).for_package_absent("cjson")
            >>> get_injector(EncoderConfig).inject(Encoder).kind
            'fast'

        Args:
            distribution: Distribution name (``importlib.metadata``)

        Returns:
            Self for method chaining
        """
        ...

    def for_package_absent(self, distribution: str) -> "BindingBuilder[T]":
        """Restrict this binding to when the distribution is not installed.

        Sugar for ``for_package_version(distribution, \"!\")``. Matches when
        ``importlib.metadata`` reports the distribution as missing. Pair with
        :meth:`for_package_present` for an explicit both-sides choice, or use
        an unconditional fallback after ``for_package_present`` instead.

        Example:
            >>> from pyiv import Config, get_injector
            >>> class Encoder:
            ...     kind = "base"
            >>> class FastEncoder(Encoder):
            ...     kind = "fast"
            >>> class StdEncoder(Encoder):
            ...     kind = "std"
            >>> class EncoderConfig(Config):
            ...     def configure(self):
            ...         b = self.get_binder()
            ...         b.bind(Encoder).to(FastEncoder).for_package_present(
            ...             "pyiv-definitely-not-installed-xyz"
            ...         )
            ...         b.bind(Encoder).to(StdEncoder).for_package_absent(
            ...             "pyiv-definitely-not-installed-xyz"
            ...         )
            >>> get_injector(EncoderConfig).inject(Encoder).kind
            'std'

        Args:
            distribution: Distribution name (``importlib.metadata``)

        Returns:
            Self for method chaining
        """
        ...

    def for_python_version(self, specifier: str) -> "BindingBuilder[T]":
        """Restrict this binding to the running interpreter's PEP 440 version.

        See the :class:`BindingBuilder` class docstring for a runnable
        ``for_python_version`` example (with
        :class:`~pyiv.version.FixedPythonVersionProvider`).

        Args:
            specifier: PEP 440 version specifier against ``sys.version_info``

        Returns:
            Self for method chaining
        """
        ...


class Binder(Protocol):
    """Fluent configuration API for contributing bindings to a ``Config``.

    **Why this exists:** Direct ``Config.register*`` calls work, but complex
    graphs read better as ``bind(X).to(Y).in_scope(Z)``. The binder also
    supports ``install``, ``expose``, version-conditioned bindings (including
    ``for_package_present`` / ``for_package_absent``), and
    ``require_explicit_bindings``.

    Example:
        >>> from pyiv import Config, get_injector
        >>> class Database:
        ...     pass
        >>> class PostgreSQL(Database):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.get_binder().bind(Database).to(PostgreSQL)
        >>> isinstance(get_injector(MyConfig).inject(Database), PostgreSQL)
        True

    Version-conditioned bindings (env-stable selection at injector build):

        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import FixedPythonVersionProvider, PythonVersionProvider
        >>> class Runner:
        ...     kind = "base"
        >>> class Legacy(Runner):
        ...     kind = "legacy"
        >>> class Modern(Runner):
        ...     kind = "modern"
        >>> class RunnerConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         b.bind(PythonVersionProvider).to_instance(
        ...             FixedPythonVersionProvider("3.12.0")
        ...         )
        ...         b.bind(Runner).to(Legacy).for_python_version("<3.11")
        ...         b.bind(Runner).to(Modern).for_python_version(">=3.11")
        >>> get_injector(RunnerConfig).inject(Runner).kind
        'modern'

    Package present / absent (optional accelerator)::

        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import MapVersionSource, package_version_domain
        >>> class Encoder:
        ...     kind = "base"
        >>> class Fast(Encoder):
        ...     kind = "fast"
        >>> class Std(Encoder):
        ...     kind = "std"
        >>> domain = package_version_domain("cjson")
        >>> class EncoderConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         b.version_source(domain, MapVersionSource({domain: "1.0"}))
        ...         b.bind(Encoder).to(Fast).for_package_present("cjson")
        ...         b.bind(Encoder).to(Std).for_package_absent("cjson")
        >>> get_injector(EncoderConfig).inject(Encoder).kind
        'fast'
    """

    def bind(self, abstract: Type[T]) -> BindingBuilder[T]:
        """Start a binding configuration.

        Args:
            abstract: The abstract type to bind

        Returns:
            A binding builder for fluent configuration
        """
        ...

    def bind_key(self, key: Key[T]) -> BindingBuilder[T]:
        """Start a binding configuration with a qualified key.

        Register with :class:`~pyiv.key.Named` (scalar or tag list/tuple).
        :class:`~pyiv.key.Matched` is inject-only and rejected at registration.
        Duplicate Named tag sets for the same type raise; at most one
        ``Named(..., default=True)`` per type is allowed.

        Args:
            key: The qualified key to bind (``Named``, not ``Matched``)

        Returns:
            A binding builder for fluent configuration
        """
        ...

    def bind_instance(self, abstract: Type[T], instance: T) -> None:
        """Bind to a pre-created instance.

        Args:
            abstract: The abstract type
            instance: The pre-created instance
        """
        ...

    def install(self, config: Any) -> None:
        """Install another configuration module.

        Args:
            config: Another Config instance or subclass to install.
                Later installs overwrite the same type/key (last wins).
        """
        ...

    def expose(self, type_or_key: Any) -> None:
        """Expose a private binding to the parent environment.

        Only meaningful on a :class:`~pyiv.config.PrivateConfig`.
        """
        ...

    def require_explicit_bindings(self) -> None:
        """Require every injectable type to be bound explicitly (no JIT)."""
        ...

    def version_source(self, domain: str, source: Any) -> None:
        """Register a :class:`~pyiv.version.VersionSource` for ``domain``."""
        ...

    def version_parser(self, name: str, parser: Any) -> None:
        """Register a named :class:`~pyiv.version.VersionParser`."""
        ...

    def use_version_parser(self, domain: str, parser_name: str) -> None:
        """Point ``domain`` at a named :class:`~pyiv.version.VersionParser`."""
        ...
