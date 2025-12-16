"""Base SerDe interface for serialization/deserialization.

This module defines the abstract base class for all SerDe implementations.
SerDe is a chain handler for the ENCODING chain type. All serialization
implementations must inherit from SerDe and implement the serialize() and
deserialize() methods.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pyiv.chain import ChainHandler, ChainType

T = TypeVar("T")


class SerDe(ChainHandler):
    """Abstract base class for serialization/deserialization operations.

    SerDe (Serialize/Deserialize) is a chain handler for the ENCODING chain type.
    It provides a unified interface for converting objects to and from various
    encoding formats (JSON, base64, uuencode, YAML, XML, pickle, etc.).

    Subclasses must implement:
        - handler_type: Return the encoding type identifier (e.g., "json", "base64", "pickle")
        - serialize(): Convert a Python object to encoded bytes/string
        - deserialize(): Convert encoded bytes/string back to a Python object

    The handler_type property identifies the format (e.g., "json", "base64", "pickle").
    Multiple implementations of the same handler_type can exist with different
    behaviors (e.g., date formatting, null handling, etc.).

    Example:
        >>> class MyJSONSerDe(SerDe):
        ...     @property
        ...     def handler_type(self) -> str:
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
    def chain_type(self) -> ChainType:
        """Return the chain type (always ENCODING for SerDe).

        Returns:
            ChainType.ENCODING
        """
        return ChainType.ENCODING

    @property
    @abstractmethod
    def handler_type(self) -> str:
        """Return the encoding type identifier (e.g., "json", "base64", "pickle").

        Returns:
            A string identifying the encoding format
        """
        pass

    def handle(self, request: Any, **kwargs) -> Any:
        """Handle a serialization/deserialization request.

        This is the chain handler interface. For SerDe, requests can be:
        - A tuple of ("serialize", obj) -> returns serialized data
        - A tuple of ("deserialize", data, target_type) -> returns deserialized object
        - A dict with "action" key -> processes accordingly

        Args:
            request: The request (can be tuple, dict, or direct object)
            **kwargs: Additional keyword arguments

        Returns:
            The result of the operation
        """
        if isinstance(request, tuple) and len(request) >= 2:
            action, *args = request
            if action == "serialize":
                return self.serialize(args[0])
            elif action == "deserialize":
                target_type = args[1] if len(args) > 1 else None
                return self.deserialize(args[0], target_type)
        elif isinstance(request, dict):
            action = request.get("action")
            if action == "serialize":
                return self.serialize(request.get("obj"))
            elif action == "deserialize":
                return self.deserialize(
                    request.get("data"), request.get("target_type")
                )
        # Default: treat as serialize request
        return self.serialize(request)

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

