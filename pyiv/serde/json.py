"""JSON SerDe implementations.

This module provides multiple JSON serialization/deserialization implementations
with different behaviors for various use cases:
    - StandardJSONSerDe: Standard Python json module behavior
    - GRPCJSONSerDe: gRPC-compatible JSON serialization
    - JSONSerDe: Base class for custom JSON implementations
"""

import json
from datetime import datetime
from typing import Any, TypeVar

from pyiv.serde.base import SerDe

T = TypeVar("T")


class JSONSerDe(SerDe):
    """Base class for JSON SerDe implementations.

    Provides common JSON serialization functionality that can be extended
    for specific use cases (gRPC, custom date formatting, etc.).
    """

    @property
    def encoding_type(self) -> str:
        """Return the encoding type identifier."""
        return "json"

    def serialize(self, obj: Any) -> str:
        """Serialize a Python object to JSON string.

        Args:
            obj: The Python object to serialize

        Returns:
            JSON string representation
        """
        return json.dumps(obj, default=self._default_serializer)

    def deserialize(self, data: str | bytes, target_type: type[T] | None = None) -> T:
        """Deserialize JSON string/bytes back to a Python object.

        Args:
            data: The JSON string or bytes
            target_type: Optional type hint for the expected result type

        Returns:
            Deserialized Python object
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)

    def _default_serializer(self, obj: Any) -> Any:
        """Default serializer for non-serializable objects.

        Subclasses can override this to customize serialization behavior
        (e.g., date formatting, custom object handling).

        Args:
            obj: Object that couldn't be serialized by default

        Returns:
            Serializable representation of the object

        Raises:
            TypeError: If object cannot be serialized
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class StandardJSONSerDe(JSONSerDe):
    """Standard JSON SerDe using Python's json module.

    Uses default Python json behavior with ISO format datetime serialization.
    """

    def serialize(self, obj: Any) -> str:
        """Serialize using standard JSON encoding.

        Args:
            obj: The Python object to serialize

        Returns:
            JSON string representation
        """
        return json.dumps(obj, default=self._default_serializer, indent=None, separators=(",", ":"))


class GRPCJSONSerDe(JSONSerDe):
    """gRPC-compatible JSON SerDe.

    Provides JSON serialization compatible with gRPC's JSON mapping.
    Handles special gRPC types and formatting requirements.
    """

    def serialize(self, obj: Any) -> str:
        """Serialize using gRPC-compatible JSON encoding.

        Args:
            obj: The Python object to serialize

        Returns:
            gRPC-compatible JSON string representation
        """
        # gRPC JSON uses compact format (no indentation)
        return json.dumps(obj, default=self._default_serializer, separators=(",", ":"))

    def _default_serializer(self, obj: Any) -> Any:
        """gRPC-compatible serializer.

        Handles gRPC-specific types and formatting.
        """
        if isinstance(obj, datetime):
            # gRPC uses RFC3339 format for timestamps
            return obj.isoformat() + "Z" if obj.tzinfo is None else obj.isoformat()
        # Handle other gRPC types if needed (e.g., Duration, Timestamp)
        return super()._default_serializer(obj)

