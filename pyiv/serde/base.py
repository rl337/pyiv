"""Base SerDe interface for serialization/deserialization.

This module defines the abstract base class for all SerDe implementations.
All serialization implementations must inherit from SerDe and implement
the serialize() and deserialize() methods.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

T = TypeVar("T")


class SerDe(ABC):
    """Abstract base class for serialization/deserialization operations.

    SerDe (Serialize/Deserialize) provides a unified interface for converting
    objects to and from various encoding formats (JSON, MessagePack, TOML, etc.).

    Subclasses must implement:
        - serialize(): Convert a Python object to encoded bytes/string
        - deserialize(): Convert encoded bytes/string back to a Python object

    The encoding_type property identifies the format (e.g., "json", "msgpack", "toml").
    Multiple implementations of the same encoding_type can exist with different
    behaviors (e.g., date formatting, null handling, etc.).

    Example:
        >>> class MyJSONSerDe(SerDe):
        ...     @property
        ...     def encoding_type(self) -> str:
        ...         return "json"
        ...
        ...     def serialize(self, obj: Any) -> str:
        ...         import json
        ...         return json.dumps(obj)
        ...
        ...     def deserialize(self, data: str, target_type: type[T]) -> T:
        ...         import json
        ...         return json.loads(data)
    """

    @property
    @abstractmethod
    def encoding_type(self) -> str:
        """Return the encoding type identifier (e.g., "json", "msgpack", "toml").

        Returns:
            A string identifying the encoding format
        """
        pass

    @abstractmethod
    def serialize(self, obj: Any) -> str | bytes:
        """Serialize a Python object to encoded format.

        Args:
            obj: The Python object to serialize

        Returns:
            Serialized representation as string or bytes
        """
        pass

    @abstractmethod
    def deserialize(self, data: str | bytes, target_type: type[T] | None = None) -> T:
        """Deserialize encoded data back to a Python object.

        Args:
            data: The encoded data (string or bytes)
            target_type: Optional type hint for the expected result type

        Returns:
            Deserialized Python object
        """
        pass

