"""Base SerDe interface for serialization/deserialization.

This module defines the abstract base class for all SerDe implementations.
SerDe is a chain handler for the ENCODING chain type. All serialization
implementations must inherit from SerDe and implement the serialize() and
deserialize() methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar, Union

from pyiv.chain import ChainHandler, ChainType

T = TypeVar("T")


class SerDe(ChainHandler):
    """Abstract base class for serialization/deserialization operations.

    SerDe is a chain handler for the ENCODING chain. Subclass it for each
    codec (JSON, base64, XML, pickle, etc.); YAML lives in ``pyiv-common``.

    Use this when callers should pick a codec by ``handler_type`` instead of
    hard-coding ``json.dumps`` / ``pickle.loads``. Register implementations on
    the ENCODING chain so injectors and pipelines can swap formats without
    rewriting call sites. Multiple handlers may share a ``handler_type`` with
    different behaviors (date formatting, null handling, and so on).

    Subclasses must implement ``handler_type``, ``serialize``, and
    ``deserialize``.

    Example:
        >>> import json
        >>> from typing import Any, Optional, Type
        >>> from pyiv.serde.base import SerDe
        >>> class MyJSONSerDe(SerDe):
        ...     @property
        ...     def handler_type(self) -> str:
        ...         return "json"
        ...     def serialize(self, obj: Any) -> str:
        ...         return json.dumps(obj)
        ...     def deserialize(
        ...         self, data: str, target_type: Optional[Type] = None
        ...     ) -> Any:
        ...         return json.loads(data)
        >>> serde = MyJSONSerDe()
        >>> serde.deserialize(serde.serialize({"a": 1}))
        {'a': 1}
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
                data = request.get("data")
                target_type = request.get("target_type")
                if data is not None:
                    return self.deserialize(data, target_type)
                return None
        # Default: treat as serialize request
        return self.serialize(request)

    @abstractmethod
    def serialize(self, obj: Any) -> Union[str, bytes]:
        """Serialize a Python object to encoded format.

        Args:
            obj: The Python object to serialize

        Returns:
            Serialized representation as string or bytes
        """
        pass

    @abstractmethod
    def deserialize(self, data: Union[str, bytes], target_type: Optional[Type[T]] = None) -> T:
        """Deserialize encoded data back to a Python object.

        Args:
            data: The encoded data (string or bytes)
            target_type: Optional type hint for the expected result type

        Returns:
            Deserialized Python object
        """
        pass
