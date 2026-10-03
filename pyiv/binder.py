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
- **Contextual overrides**: ``.when_injected_into(Owner)`` keeps a default
  binding while swapping the implementation for one consumer class

**Real-World Use Cases:**

- **Dynamic Configuration**: Build configurations based on environment variables
- **Configuration Testing**: Mock binders to test configuration logic
- **Modular Configuration**: Compose configurations from multiple sources
- **Framework Integration**: Provide fluent APIs for framework-specific configuration
- **Per-consumer implementations**: JSON everywhere, Avro only inside a producer
  (without ``Named`` on every constructor)

Architecture:
    - Binder: Protocol defining the binder interface
    - BindingBuilder: Fluent builder for configuring bindings
      (``.to`` / ``.in_scope`` / ``.when_injected_into`` / …)
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

    Contextual Binding For One Consumer:

    Prefer this over ``Named`` when the *owner class* should pick the
    implementation. ``AvroProducer`` keeps a bare ``encoder: Encoder``
    parameter; the binder graph supplies ``AvroEncoder`` only for that owner.
    Other inject sites still see the default.

        >>> from pyiv import Config, get_injector
        >>> class Serializer:
        ...     def __init__(self, format: str = "none"):
        ...         self.format = format
        >>> class JsonSerializer(Serializer):
        ...     def __init__(self):
        ...         super().__init__("json")
        >>> class ProtobufSerializer(Serializer):
        ...     def __init__(self):
        ...         super().__init__("protobuf")
        >>> class EventPublisher:
        ...     def __init__(self, serializer: Serializer):
        ...         self.serializer = serializer
        >>> class AuditLogger:
        ...     def __init__(self, serializer: Serializer):
        ...         self.serializer = serializer
        >>> class PubConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         b.bind(Serializer).to(JsonSerializer)
        ...         b.bind(Serializer).to(ProtobufSerializer).when_injected_into(
        ...             EventPublisher
        ...         )
        ...         b.bind(EventPublisher).to(EventPublisher)
        ...         b.bind(AuditLogger).to(AuditLogger)
        >>> pub = get_injector(PubConfig)
        >>> pub.inject(AuditLogger).serializer.format
        'json'
        >>> pub.inject(EventPublisher).serializer.format
        'protobuf'
        >>> pub.inject(Serializer, from_=EventPublisher).format
        'protobuf'
"""

from typing import Any, Generic, Protocol, Type, TypeVar

from pyiv.key import Key
from pyiv.provider import Provider
from pyiv.scope import Scope

T = TypeVar("T")


class BindingBuilder(Protocol, Generic[T]):
    """Fluent steps after :meth:`Binder.bind` (``.to`` / ``.in_scope`` / …).

    **Why this exists:** A single ``register(...)`` call buries scope and
    provider choices in kwargs. The builder makes the binding shape readable
    as a chain while still writing the same ``Config`` store.

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

        Contextual override (when-injected-into):
        >>> class Encoder:
        ...     def __init__(self, kind: str = "base"):
        ...         self.kind = kind
        >>> class JSONEncoder(Encoder):
        ...     def __init__(self):
        ...         super().__init__("json")
        >>> class AvroEncoder(Encoder):
        ...     def __init__(self):
        ...         super().__init__("avro")
        >>> class AvroProducer:
        ...     def __init__(self, encoder: Encoder):
        ...         self.encoder = encoder
        >>> class CtxConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         b.bind(Encoder).to(JSONEncoder)
        ...         b.bind(Encoder).to(AvroEncoder).when_injected_into(AvroProducer)
        ...         b.bind(AvroProducer).to(AvroProducer)
        >>> inj = get_injector(CtxConfig)
        >>> inj.inject(Encoder).kind
        'json'
        >>> inj.inject(AvroProducer).encoder.kind
        'avro'
        >>> inj.inject(Encoder, from_=AvroProducer).kind
        'avro'
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

    def when_injected_into(self, owner: Type) -> "BindingBuilder[T]":
        """Limit this binding to requests made while injecting into ``owner``.

        Exact type match only (no subclass walk). Does not replace the default
        unqualified binding for the abstract type. Use
        ``inject(T, from_=owner)`` for manual lookups. See the
        :class:`BindingBuilder` class example for a full Encoder / AvroProducer
        walkthrough.

        Args:
            owner: The requesting class that should see this binding

        Returns:
            Self for method chaining
        """
        ...


class Binder(Protocol):
    """Fluent configuration API for contributing bindings to a ``Config``.

    **Why this exists:** Direct ``Config.register*`` calls work, but complex
    graphs read better as ``bind(X).to(Y).in_scope(Z)`` or
    ``bind(X).to(Y).when_injected_into(Owner)``. The binder also supports
    ``install``, ``expose``, and ``require_explicit_bindings``. See the
    module docstring for a Serializer / EventPublisher contextual example.

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
