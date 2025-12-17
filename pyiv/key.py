"""Key and Qualifier for type-safe qualified bindings.

This module provides Key and Qualifier interfaces for creating type-safe
qualified bindings. This allows multiple implementations of the same type
to be distinguished using qualifiers (like @Named in Guice).

**What Problem Does This Solve?**

Keys solve the "multiple implementations" problem:
- **Type Safety**: Distinguish between multiple implementations of the same type
  without using string-based names (which are error-prone)
- **IDE Support**: Better autocomplete and type checking than string qualifiers
- **Compile-Time Safety**: Catch binding errors at configuration time, not runtime
- **Clear Intent**: Makes it explicit which implementation is being used

**Real-World Use Cases:**
- **Multiple Database Connections**: Primary vs replica databases
- **Different Logger Implementations**: File logger vs console logger vs remote logger
- **Environment-Specific Configs**: Development vs production vs test configurations
- **Input/Output Serializers**: Different JSON serializers for input vs output

Architecture:
    - Key: Type-safe key for qualified bindings
    - Qualifier: Protocol for qualifier annotations
    - Named: Built-in string-based qualifier

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
        ...         # Bind with qualifiers
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

    Using Keys for Different Implementations:
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
        >>> # Create keys for different logger implementations
        >>> file_key = Key(Logger, Named("file"))
        >>> console_key = Key(Logger, Named("console"))
        >>>
        >>> # Keys are hashable and can be used in dictionaries
        >>> bindings = {
        ...     file_key: FileLogger,
        ...     console_key: ConsoleLogger,
        ... }
        >>> bindings[file_key]
        <class '...FileLogger'>
"""

from typing import Any, Generic, Optional, Protocol, Type, TypeVar

T = TypeVar("T")


class Qualifier(Protocol):
    """Protocol for qualifier annotations.

    Qualifiers are used to distinguish between multiple implementations
    of the same type. They can be annotations, strings, or custom objects.

    Example:
        class Named(Qualifier):
            def __init__(self, name: str):
                self.name = name
    """

    pass


class Named:
    """String-based qualifier for named bindings.

    This is the most common qualifier type, allowing bindings to be
    distinguished by a string name.

    Example:
        >>> from pyiv.key import Named
        >>>
        >>> primary = Named("primary")
        >>> replica = Named("replica")
    """

    def __init__(self, name: str):
        """Initialize named qualifier.

        Args:
            name: The name identifier
        """
        if not isinstance(name, str) or not name:
            raise ValueError(f"name must be a non-empty string, got {name}")
        self.name = name

    def __eq__(self, other: Any) -> bool:
        """Check equality with another Named qualifier.

        Args:
            other: The other object to compare

        Returns:
            True if both are Named with the same name
        """
        return isinstance(other, Named) and self.name == other.name

    def __hash__(self) -> int:
        """Hash the qualifier.

        Returns:
            Hash value based on the name
        """
        return hash(("Named", self.name))

    def __repr__(self) -> str:
        """String representation.

        Returns:
            String representation of the qualifier
        """
        return f"Named({self.name!r})"


class Key(Generic[T]):
    """Type-safe key for qualified bindings.

    A Key combines a type with an optional qualifier to create a unique
    binding key. This allows multiple implementations of the same type to
    be registered and injected.

    Example:
        >>> from pyiv.key import Key, Named
        >>>
        >>> # Key without qualifier (default binding)
        >>> default_key = Key(Database)
        >>>
        >>> # Key with qualifier
        >>> primary_key = Key(Database, Named("primary"))
        >>> replica_key = Key(Database, Named("replica"))
    """

    def __init__(self, type: Type[T], qualifier: Optional[Qualifier] = None):
        """Initialize a key.

        Args:
            type: The type to bind
            qualifier: Optional qualifier to distinguish this binding

        Raises:
            TypeError: If type is not a type
        """
        if not isinstance(type, type):
            type_name = type.__class__.__name__ if hasattr(type, "__class__") else str(type)
            raise TypeError(f"type must be a type, got {type_name}")
        self.type = type
        self.qualifier = qualifier

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
