"""YAML SerDe for pyiv, backed by PyYAML.

This module provides ``YAMLSerDe``, a ``pyiv.serde.SerDe`` implementation
that uses PyYAML. Infrastructure (``SerDe``, chain handlers) stays in core.

**What Problem Does This Solve?**

YAML is a common config and payload format, but PyYAML is not in the
Python standard library. Core pyiv must not import it. This extra ships
the YAML codec without changing the SerDe API.

**Real-World Use Cases:**
- Load YAML config documents through the injector
- Encode/decode YAML payloads on an ENCODING chain

Example:

    >>> from pyiv_common.serde import YAMLSerDe
    >>> serde = YAMLSerDe()
    >>> serde.handler_type
    'yaml'
    >>> data = serde.serialize({"key": "value"})
    >>> serde.deserialize(data)["key"]
    'value'
"""

from typing import Any, Optional, Type, TypeVar, Union

import yaml  # type: ignore[import-untyped]

from pyiv.serde.base import SerDe

T = TypeVar("T")


class YAMLSerDe(SerDe):
    """YAML encoding SerDe using PyYAML.

    Install with ``pip install pyiv-common``. Register on the ENCODING
    chain like any other ``SerDe``.

    Example:
        >>> from pyiv import ChainType, Config, get_injector
        >>> from pyiv_common.serde import YAMLSerDe
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register_chain_handler(ChainType.ENCODING, "yaml", YAMLSerDe)
        >>> injector = get_injector(MyConfig)
        >>> serde = injector.inject_chain_handler(ChainType.ENCODING, "yaml")
        >>> serde.deserialize(serde.serialize({"a": 1}))
        {'a': 1}
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier ("yaml")."""
        return "yaml"

    def serialize(self, obj: Any) -> str:
        """Serialize using YAML encoding.

        Args:
            obj: The Python object to serialize

        Returns:
            YAML string representation
        """
        return yaml.dump(obj, default_flow_style=False)

    def deserialize(self, data: Union[str, bytes], target_type: Optional[Type[T]] = None) -> T:
        """Deserialize YAML string/bytes back to a Python object.

        Args:
            data: The YAML string or bytes
            target_type: Optional type hint for the expected result type

        Returns:
            Deserialized Python object
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return yaml.safe_load(data)
