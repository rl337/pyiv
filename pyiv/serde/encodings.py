"""Standard Python encoding SerDe implementations.

This module provides SerDe implementations for encoding formats available
in Python's standard library:
    - JSON: Standard JSON encoding
    - Base64: Base64 encoding
    - UUEncode: UU encoding
    - YAML: YAML encoding (if available)
    - XML: XML encoding
    - Pickle: Python pickle encoding (default/no-op fallback)
    - NoOp: No-op encoding (pass-through)
"""

import base64
import io
import json
import pickle
import xml.etree.ElementTree as ET
from typing import Any, Optional, Type, TypeVar, Union

# uu is a standard library module, but import it explicitly
try:
    import uu

    UU_AVAILABLE = True
except ImportError:
    UU_AVAILABLE = False

# Try to import yaml (not in standard library, but commonly available)
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from pyiv.serde.base import SerDe

T = TypeVar("T")


class NoOpSerDe(SerDe):
    """No-op SerDe that passes through data unchanged.

    This is the default fallback when no encoding is specified.
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier."""
        return "noop"

    def serialize(self, obj: Any) -> Union[str, bytes]:
        """Pass through the object unchanged.

        Args:
            obj: The Python object to serialize

        Returns:
            The object unchanged (as string or bytes)
        """
        if isinstance(obj, (str, bytes)):
            return obj
        return str(obj)

    def deserialize(
        self, data: Union[str, bytes], target_type: Optional[Type[T]] = None
    ) -> T:
        """Pass through the data unchanged.

        Args:
            data: The encoded data (string or bytes)
            target_type: Optional type hint (ignored)

        Returns:
            The data unchanged
        """
        return data  # type: ignore[return-value]


class PickleSerDe(SerDe):
    """Python pickle SerDe.

    Uses Python's pickle module for serialization. This is a fallback option
    when other encodings are not suitable.
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier."""
        return "pickle"

    def serialize(self, obj: Any) -> bytes:
        """Serialize using pickle.

        Args:
            obj: The Python object to serialize

        Returns:
            Pickled bytes representation
        """
        return pickle.dumps(obj)

    def deserialize(
        self, data: Union[str, bytes], target_type: Optional[Type[T]] = None
    ) -> T:
        """Deserialize using pickle.

        Args:
            data: The pickled data (bytes)
            target_type: Optional type hint (ignored, pickle handles types)

        Returns:
            Deserialized Python object
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        return pickle.loads(data)


class JSONSerDe(SerDe):
    """Standard JSON SerDe using Python's json module."""

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier."""
        return "json"

    def serialize(self, obj: Any) -> str:
        """Serialize using standard JSON encoding.

        Args:
            obj: The Python object to serialize

        Returns:
            JSON string representation
        """
        return json.dumps(obj, default=self._default_serializer)

    def deserialize(
        self, data: Union[str, bytes], target_type: Optional[Type[T]] = None
    ) -> T:
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

        Args:
            obj: Object that couldn't be serialized by default

        Returns:
            Serializable representation of the object

        Raises:
            TypeError: If object cannot be serialized
        """
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class Base64SerDe(SerDe):
    """Base64 encoding SerDe.

    Encodes/decodes data using base64 encoding. Input must be bytes.
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier."""
        return "base64"

    def serialize(self, obj: Any) -> str:
        """Serialize using base64 encoding.

        Args:
            obj: The data to encode (bytes or string)

        Returns:
            Base64-encoded string
        """
        if isinstance(obj, str):
            obj = obj.encode("utf-8")
        elif not isinstance(obj, bytes):
            obj = pickle.dumps(obj)  # Fallback to pickle for complex objects
        return base64.b64encode(obj).decode("utf-8")

    def deserialize(
        self, data: Union[str, bytes], target_type: Optional[Type[T]] = None
    ) -> T:
        """Deserialize base64-encoded data.

        Args:
            data: The base64-encoded string or bytes
            target_type: Optional type hint (returns bytes by default)

        Returns:
            Decoded bytes
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        return base64.b64decode(data)  # type: ignore[return-value]


class UUEncodeSerDe(SerDe):
    """UU encoding SerDe.

    Encodes/decodes data using UU encoding. Input must be bytes.
    Requires the uu module from Python's standard library.
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier."""
        return "uuencode"

    def serialize(self, obj: Any) -> str:
        """Serialize using UU encoding.

        Args:
            obj: The data to encode (bytes or string)

        Returns:
            UU-encoded string

        Raises:
            ImportError: If uu module is not available
        """
        if not UU_AVAILABLE:
            raise ImportError("uu module is not available in this Python installation")
        if isinstance(obj, str):
            obj = obj.encode("utf-8")
        elif not isinstance(obj, bytes):
            obj = pickle.dumps(obj)  # Fallback to pickle for complex objects

        output = io.StringIO()
        input_data = io.BytesIO(obj)
        uu.encode(input_data, output)
        return output.getvalue()

    def deserialize(
        self, data: Union[str, bytes], target_type: Optional[Type[T]] = None
    ) -> T:
        """Deserialize UU-encoded data.

        Args:
            data: The UU-encoded string or bytes
            target_type: Optional type hint (returns bytes by default)

        Returns:
            Decoded bytes

        Raises:
            ImportError: If uu module is not available
        """
        if not UU_AVAILABLE:
            raise ImportError("uu module is not available in this Python installation")
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        input_data = io.StringIO(data)
        output = io.BytesIO()
        uu.decode(input_data, output)
        return output.getvalue()  # type: ignore[return-value]


class XMLSerDe(SerDe):
    """XML encoding SerDe.

    Encodes/decodes data using XML. For simple dict/list structures.
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier."""
        return "xml"

    def serialize(self, obj: Any) -> str:
        """Serialize using XML encoding.

        Args:
            obj: The Python object to serialize (dict or list)

        Returns:
            XML string representation
        """
        if isinstance(obj, dict):
            root = ET.Element("root")
            self._dict_to_xml(obj, root)
        elif isinstance(obj, list):
            root = ET.Element("root")
            for item in obj:
                elem = ET.SubElement(root, "item")
                if isinstance(item, dict):
                    self._dict_to_xml(item, elem)
                else:
                    elem.text = str(item)
        else:
            root = ET.Element("root")
            root.text = str(obj)

        return ET.tostring(root, encoding="unicode")

    def deserialize(
        self, data: Union[str, bytes], target_type: Optional[Type[T]] = None
    ) -> T:
        """Deserialize XML string/bytes back to a Python object.

        Args:
            data: The XML string or bytes
            target_type: Optional type hint (returns dict by default)

        Returns:
            Deserialized Python object (dict or list)
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        root = ET.fromstring(data)
        return self._xml_to_dict(root)  # type: ignore[return-value]

    def _dict_to_xml(self, d: dict, parent: ET.Element) -> None:
        """Convert dict to XML elements."""
        for key, value in d.items():
            elem = ET.SubElement(parent, str(key))
            if isinstance(value, dict):
                self._dict_to_xml(value, elem)
            elif isinstance(value, list):
                for item in value:
                    item_elem = ET.SubElement(elem, "item")
                    if isinstance(item, dict):
                        self._dict_to_xml(item, item_elem)
                    else:
                        item_elem.text = str(item)
            else:
                elem.text = str(value)

    def _xml_to_dict(self, elem: ET.Element) -> dict | list | str:
        """Convert XML element to dict/list."""
        if len(elem) == 0:
            return elem.text or ""
        result = {}
        for child in elem:
            if child.tag == "item":
                if "items" not in result:
                    result["items"] = []
                result["items"].append(self._xml_to_dict(child))
            else:
                result[child.tag] = self._xml_to_dict(child)
        return result


class YAMLSerDe(SerDe):
    """YAML encoding SerDe.

    Uses PyYAML if available, otherwise raises ImportError.
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier."""
        return "yaml"

    def serialize(self, obj: Any) -> str:
        """Serialize using YAML encoding.

        Args:
            obj: The Python object to serialize

        Returns:
            YAML string representation

        Raises:
            ImportError: If PyYAML is not available
        """
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML is not installed. Install it with: pip install pyyaml")
        return yaml.dump(obj, default_flow_style=False)

    def deserialize(
        self, data: Union[str, bytes], target_type: Optional[Type[T]] = None
    ) -> T:
        """Deserialize YAML string/bytes back to a Python object.

        Args:
            data: The YAML string or bytes
            target_type: Optional type hint for the expected result type

        Returns:
            Deserialized Python object

        Raises:
            ImportError: If PyYAML is not available
        """
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML is not installed. Install it with: pip install pyyaml")
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return yaml.safe_load(data)

