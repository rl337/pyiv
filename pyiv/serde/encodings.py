"""Standard Python encoding SerDe implementations.

This module provides SerDe implementations for encoding formats available
in Python's standard library:

- JSON: Standard JSON encoding
- Base64: Base64 encoding
- XML: XML encoding
- Pickle: Python pickle encoding (default/no-op fallback)
- NoOp: No-op encoding (pass-through)

YAML lives in ``pyiv-common`` (``from pyiv_common.serde import YAMLSerDe``).
"""

import base64
import json
import pickle
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pyiv.serde.base import SerDe

T = TypeVar("T")


class NoOpSerDe(SerDe):
    """No-op SerDe that passes through data unchanged.

    Use this as the default when no encoding is configured, or when a pipeline
    already holds strings/bytes and must not re-encode them. Strings and bytes
    are returned as-is; other objects become ``str(obj)``.

    **Why this exists:** Default pass-through encoder when no wire format was configured.


    Example:
        >>> from pyiv.serde.encodings import NoOpSerDe
        >>> serde = NoOpSerDe()
        >>> serde.handler_type
        'noop'
        >>> serde.serialize("already-encoded")
        'already-encoded'
        >>> serde.deserialize("already-encoded")
        'already-encoded'
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier.

        Returns:
            The handler type identifier ("noop")
        """
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

    def deserialize(self, data: Union[str, bytes], target_type: Optional[Type[T]] = None) -> T:
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

    Use this when you need to round-trip arbitrary Python objects that JSON,
    XML, or base64 text cannot represent. Prefer safer text codecs for
    untrusted input; pickle is a stdlib fallback for trusted local data.

    Example:
        >>> from pyiv.serde.encodings import PickleSerDe
        >>> serde = PickleSerDe()
        >>> serde.handler_type
        'pickle'
        >>> serde.deserialize(serde.serialize({"x": 2}))
        {'x': 2}
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier.

        Returns:
            The handler type identifier ("pickle")
        """
        return "pickle"

    def serialize(self, obj: Any) -> bytes:
        """Serialize using pickle.

        Args:
            obj: The Python object to serialize

        Returns:
            Pickled bytes representation
        """
        return pickle.dumps(obj)

    def deserialize(self, data: Union[str, bytes], target_type: Optional[Type[T]] = None) -> T:
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
    """Standard JSON SerDe using Python's ``json`` module.

    Use this for APIs, configs, and payloads that exchange JSON. Datetimes
    serialize to ISO strings; objects with ``__dict__`` become dicts. Prefer
    this over pickle whenever the data is text-safe and interoperable.

    Example:
        >>> from pyiv.serde.encodings import JSONSerDe
        >>> serde = JSONSerDe()
        >>> serde.handler_type
        'json'
        >>> serde.serialize({"a": 1})
        '{"a": 1}'
        >>> serde.deserialize('{"a": 1}')
        {'a': 1}
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier.

        Returns:
            The handler type identifier ("json")
        """
        return "json"

    def serialize(self, obj: Any) -> str:
        """Serialize using standard JSON encoding.

        Args:
            obj: The Python object to serialize

        Returns:
            JSON string representation
        """
        return json.dumps(obj, default=self._default_serializer)

    def deserialize(self, data: Union[str, bytes], target_type: Optional[Type[T]] = None) -> T:
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
        from datetime import datetime

        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class Base64SerDe(SerDe):
    """Base64 encoding SerDe.

    Use this when binary payloads must travel as text (headers, logs, or
    text-only transports). Strings are UTF-8 encoded first; non-bytes objects
    fall back to pickle before encoding. Deserialize returns raw bytes.

    Example:
        >>> from pyiv.serde.encodings import Base64SerDe
        >>> serde = Base64SerDe()
        >>> serde.handler_type
        'base64'
        >>> encoded = serde.serialize(b"hello")
        >>> encoded
        'aGVsbG8='
        >>> serde.deserialize(encoded)
        b'hello'
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier.

        Returns:
            The handler type identifier ("base64")
        """
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

    def deserialize(self, data: Union[str, bytes], target_type: Optional[Type[T]] = None) -> T:
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


class XMLSerDe(SerDe):
    """XML encoding SerDe for simple dict/list structures.

    Use this when interoperability with XML-oriented systems matters and the
    payload is a shallow dict or list. Nested dicts become child elements;
    lists become ``item`` children. Not a full schema or namespace mapper.

    Example:
        >>> from pyiv.serde.encodings import XMLSerDe
        >>> serde = XMLSerDe()
        >>> serde.handler_type
        'xml'
        >>> xml = serde.serialize({"name": "Ada"})
        >>> xml
        '<root><name>Ada</name></root>'
        >>> serde.deserialize(xml)
        {'name': 'Ada'}
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier.

        Returns:
            The handler type identifier ("xml")
        """
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

    def deserialize(self, data: Union[str, bytes], target_type: Optional[Type[T]] = None) -> T:
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
        """Convert dict to XML elements.

        Args:
            d: Dictionary to convert
            parent: Parent XML element to attach to

        Returns:
            None (modifies parent in place)
        """
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

    def _xml_to_dict(self, elem: ET.Element) -> Union[Dict[str, Any], List[Any], str]:
        """Convert XML element to dict/list.

        Args:
            elem: XML element to convert

        Returns:
            Converted dict, list, or string
        """
        if len(elem) == 0:
            return elem.text or ""
        result: Dict[str, Any] = {}
        for child in elem:
            if child.tag == "item":
                if "items" not in result:
                    result["items"] = []
                items_list = result["items"]
                if isinstance(items_list, list):
                    items_list.append(self._xml_to_dict(child))
            else:
                result[child.tag] = self._xml_to_dict(child)
        return result
