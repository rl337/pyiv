"""Key and Qualifier for type-safe qualified bindings.

This module provides Key and Qualifier interfaces for creating type-safe
qualified bindings. Multiple implementations of the same type are
distinguished with qualifiers (like @Named in Guice).

**What Problem Does This Solve?**

Keys solve the "multiple implementations" problem:

- **Type Safety**: Distinguish implementations of one type without inventing wrappers
- **Tag sets**: ``Named`` accepts a string or list/tuple of tags (stored as a set)
- **Strict vs nearest match**: inject with ``Named`` (exact tags) or ``Matched``
  (required + prefer scoring, with ``default=True`` tie-breaks)
- **Constructor Annotated**: ``Annotated[T, Named(...)]`` /
  ``Annotated[T, Matched(...)]`` (also with ``Optional`` / ``Provider``)
- **Clear Intent**: Makes it explicit which implementation is being used

**Real-World Use Cases:**

- **Multiple Database Connections**: Primary vs replica databases
- **Encoders / serializers**: JSON vs YAML vs AVRO, optionally with a default
- **Environment-Specific Configs**: Development vs production vs test configurations
- **Nearest match**: Prefer a tagged binding without requiring an exact compound key

Architecture:
    - Key: Type-safe key for qualified bindings
    - Qualifier: Protocol for qualifier annotations
    - Named: Tag-set qualifier used when **registering** (and for strict inject)
    - Matched: Inject-only qualifier for required/prefer resolution

Usage Examples:

    Basic Qualified Binding:
        >>> from pyiv.key import Key, Named
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Database:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>>
        >>> class PostgreSQL(Database):
        ...     def __init__(self):
        ...         super().__init__("postgresql")
        >>>
        >>> class MySQL(Database):
        ...     def __init__(self):
        ...         super().__init__("mysql")
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register_key(Key(Database, Named("primary")), PostgreSQL)
        ...         self.register_key(Key(Database, Named("replica")), MySQL)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> primary_db = injector.inject(Key(Database, Named("primary")))
        >>> replica_db = injector.inject(Key(Database, Named("replica")))
        >>>
        >>> primary_db.name
        'postgresql'
        >>> replica_db.name
        'mysql'

    Tag Sets And Default:
        >>> from pyiv.key import Key, Named, Matched
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Encoder:
        ...     def __init__(self, kind: str):
        ...         self.kind = kind
        >>>
        >>> class JSONEncoder(Encoder):
        ...     def __init__(self):
        ...         super().__init__("json")
        >>>
        >>> class PrettyJSONEncoder(Encoder):
        ...     def __init__(self):
        ...         super().__init__("json-pretty")
        >>>
        >>> class EncoderConfig(Config):
        ...     def configure(self):
        ...         self.register_key(Key(Encoder, Named("json")), JSONEncoder)
        ...         self.register_key(
        ...             Key(Encoder, Named(["json", "pretty"], default=True)),
        ...             PrettyJSONEncoder,
        ...         )
        >>>
        >>> inj = get_injector(EncoderConfig)
        >>> Named("json") == Named(["json"])
        True
        >>> inj.inject(Key(Encoder, Named("json"))).kind
        'json'
        >>> inj.inject(Key(Encoder, Matched(required=["json"], prefer=["pretty"]))).kind
        'json-pretty'
        >>> inj.inject(Encoder).kind  # bare type uses default=True
        'json-pretty'

    Using Keys For Different Implementations:
        >>> from pyiv.key import Key, Named
        >>>
        >>> class Logger:
        ...     pass
        >>>
        >>> class FileLogger(Logger):
        ...     pass
        >>>
        >>> class ConsoleLogger(Logger):
        ...     pass
        >>>
        >>> file_key = Key(Logger, Named("file"))
        >>> console_key = Key(Logger, Named("console"))
        >>> bindings = {
        ...     file_key: FileLogger,
        ...     console_key: ConsoleLogger,
        ... }
        >>> bindings[file_key]
        <class '...FileLogger'>
"""

from typing import Any, FrozenSet, Generic, Optional, Protocol, Sequence, Type, TypeVar, Union

T = TypeVar("T")

TagInput = Union[str, Sequence[str]]


def normalize_tags(tags: Optional[TagInput], *, allow_empty: bool = False) -> FrozenSet[str]:
    """Normalize a scalar or sequence of tags to a frozenset of non-empty strings.

    Args:
        tags: A string, list/tuple of strings, or None (treated as empty)
        allow_empty: If False, empty input raises ValueError

    Returns:
        A frozenset of tag strings

    Raises:
        TypeError: If a tag is not a string, or tags is not str/list/tuple/None
        ValueError: If empty when not allowed, or a tag string is empty
    """
    if tags is None:
        result: FrozenSet[str] = frozenset()
    elif isinstance(tags, str):
        if not tags:
            raise ValueError("tag strings must be non-empty")
        result = frozenset([tags])
    elif isinstance(tags, (list, tuple)):
        normalized = []
        for tag in tags:
            if not isinstance(tag, str):
                raise TypeError(f"tags must be strings, got {type(tag).__name__}")
            if not tag:
                raise ValueError("tag strings must be non-empty")
            normalized.append(tag)
        result = frozenset(normalized)
    else:
        raise TypeError(f"tags must be a str, list, or tuple, got {type(tags).__name__}")

    if not allow_empty and not result:
        raise ValueError("tags must be non-empty")
    return result


class Qualifier(Protocol):
    """Marker for distinguishing multiple bindings of the same type.

    **Why this exists:** One interface often has several implementations
    (primary vs replica DB). A qualifier + :class:`Key` selects which binding
    to inject without inventing wrapper types.

    Example:
        >>> from pyiv.key import Named
        >>> isinstance(Named("primary"), Named)
        True
    """

    pass


class Named:
    """Tag-set qualifier for named bindings (registration and strict inject).

    **Why this exists:** Distinguish multiple implementations of one type with
    string tags. A scalar name is the common case; list/tuple tags form a set
    for compound keys. ``default=True`` marks the binding used for bare
    ``inject(Type)`` and for ``Matched`` tie-breaks.

    Accepts ``str``, ``list``, or ``tuple``; all normalize to a frozenset.
    ``Named("json") == Named(["json"])``. Equality and hashing use the tag set
    only — ``default`` is binding metadata, not part of key identity.

    Register with ``Named`` only. For nearest-match inject, use :class:`Matched`.

    **Constructor injection:** use ``Annotated[T, Named(...)]`` on ``__init__``
    parameters (also with ``Optional[T]`` / ``Provider[T]``). This does **not**
    apply to field / ``inject_members`` injection — see the keys guide.

    Example:
        >>> from pyiv.key import Named
        >>>
        >>> Named("primary") == Named(["primary"])
        True
        >>> Named(["json", "pretty"]).tags == frozenset({"json", "pretty"})
        True
        >>> Named("x", default=True) == Named("x", default=False)
        True
    """

    def __init__(self, name: TagInput, *, default: bool = False):
        """Initialize named qualifier.

        Args:
            name: A non-empty string, or a non-empty list/tuple of tag strings
            default: If True, this binding is preferred for bare type inject
                and breaks ties under :class:`Matched`

        Raises:
            TypeError: If tags are not strings or name is not str/list/tuple
            ValueError: If tags are empty
        """
        self.tags: FrozenSet[str] = normalize_tags(name, allow_empty=False)
        self.default: bool = bool(default)
        # Backward-compatible single-name attribute (scalar or sole tag).
        if len(self.tags) == 1:
            self.name: str = next(iter(self.tags))
        else:
            self.name = ",".join(sorted(self.tags))

    def __eq__(self, other: Any) -> bool:
        """Check equality with another Named qualifier (tags only).

        Args:
            other: The other object to compare

        Returns:
            True if both are Named with the same tag set (ignores default)
        """
        return isinstance(other, Named) and self.tags == other.tags

    def __hash__(self) -> int:
        """Hash the qualifier from its tag set (ignores default)."""
        return hash(("Named", self.tags))

    def __repr__(self) -> str:
        """String representation."""
        tags_repr = sorted(self.tags)
        if len(tags_repr) == 1 and not self.default:
            return f"Named({tags_repr[0]!r})"
        if self.default:
            return f"Named({tags_repr!r}, default=True)"
        return f"Named({tags_repr!r})"


class Matched:
    """Inject-only qualifier for required/prefer tag matching.

    **Why this exists:** Exact ``Named`` keys are rigid when several bindings
    share tags. ``Matched`` selects among ``Named`` registrations: every
    ``required`` tag must be present, then the binding with the most
    ``prefer`` overlap wins; ``Named(..., default=True)`` breaks remaining ties.

    Do **not** pass ``Matched`` to ``register_key`` / ``bind_key`` — registration
    uses ``Named`` only.

    **Constructor injection:** ``Annotated[T, Matched(...)]`` on ``__init__``
    (including ``Annotated[Optional[T], Matched(...)]``). Not supported on
    field / ``inject_members`` paths.

    Resolution ladder (candidates = all Named bindings for the key type):

    1. Keep bindings where ``required ⊆ binding.tags``
    2. Keep those with maximal ``|prefer ∩ binding.tags|``
    3. If still more than one, keep ``default=True``
    4. Exactly one → use it; otherwise ``CreationError``

    Example:
        >>> from pyiv.key import Key, Named, Matched
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Encoder:
        ...     def __init__(self, kind: str):
        ...         self.kind = kind
        >>>
        >>> class JSONEncoder(Encoder):
        ...     def __init__(self):
        ...         super().__init__("json")
        >>>
        >>> class PrettyJSONEncoder(Encoder):
        ...     def __init__(self):
        ...         super().__init__("pretty")
        >>>
        >>> class C(Config):
        ...     def configure(self):
        ...         self.register_key(Key(Encoder, Named("json")), JSONEncoder)
        ...         self.register_key(
        ...             Key(Encoder, Named(["json", "pretty"], default=True)),
        ...             PrettyJSONEncoder,
        ...         )
        >>>
        >>> get_injector(C).inject(
        ...     Key(Encoder, Matched(required=["json"], prefer=["pretty"]))
        ... ).kind
        'pretty'
    """

    def __init__(
        self,
        required: Optional[TagInput] = None,
        prefer: Optional[TagInput] = None,
    ):
        """Initialize matched qualifier.

        Args:
            required: Tags that must all be present on a candidate (optional)
            prefer: Tags used to score candidates; more overlap wins (optional)

        Raises:
            TypeError: If a tag is not a string
            ValueError: If a tag string is empty
        """
        self.required: FrozenSet[str] = normalize_tags(required, allow_empty=True)
        self.prefer: FrozenSet[str] = normalize_tags(prefer, allow_empty=True)

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Matched)
            and self.required == other.required
            and self.prefer == other.prefer
        )

    def __hash__(self) -> int:
        return hash(("Matched", self.required, self.prefer))

    def __repr__(self) -> str:
        return f"Matched(required={sorted(self.required)!r}, " f"prefer={sorted(self.prefer)!r})"


class Key(Generic[T]):
    """Type-safe key for qualified bindings.

    **Why this exists:** Pair a type with an optional qualifier so multiple
    implementations of one type can coexist. Use :class:`Named` when binding
    (and for strict inject). Use :class:`Matched` only when injecting for
    nearest-match resolution.

    Prefer ``Annotated[T, Named|Matched]`` on constructors when the dependency
    is a parameter; use ``inject(Key(...))`` for explicit lookups. Annotated
    qualifiers are **not** applied during ``inject_members`` field injection.

    Example:
        >>> from pyiv.key import Key, Named
        >>>
        >>> default_key = Key(int)
        >>> primary_key = Key(int, Named("primary"))
        >>> replica_key = Key(int, Named("replica"))
        >>> primary_key != replica_key
        True
        >>> Key(int, Named("a")) == Key(int, Named(["a"]))
        True
    """

    def __init__(self, binding_type: Type[T], qualifier: Optional[Qualifier] = None):
        """Initialize a key.

        Args:
            binding_type: The type to bind
            qualifier: Optional qualifier (``Named`` for register/strict inject,
                ``Matched`` for inject-only nearest match)

        Raises:
            TypeError: If binding_type is not a type
        """
        if not isinstance(binding_type, type):
            type_name = type(binding_type).__name__
            raise TypeError(f"type must be a type, got {type_name}")
        self.type: Type[T] = binding_type
        self.qualifier: Optional[Qualifier] = qualifier

    def __eq__(self, other: Any) -> bool:
        """Check equality with another Key.

        Args:
            other: The other object to compare

        Returns:
            True if both keys have the same type and qualifier
        """
        if not isinstance(other, Key):
            return False
        return self.type == other.type and self.qualifier == other.qualifier

    def __hash__(self) -> int:
        """Hash the key.

        Returns:
            Hash value based on type and qualifier
        """
        return hash((self.type, self.qualifier))

    def __repr__(self) -> str:
        """String representation.

        Returns:
            String representation of the key
        """
        type_name = getattr(self.type, "__name__", str(self.type))
        if self.qualifier:
            return f"Key({type_name}, {self.qualifier!r})"
        return f"Key({type_name})"
