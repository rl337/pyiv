"""JSON SerDe implementation.

This module provides the JSON SerDe implementation as a re-export from
the encodings module for backward compatibility and convenience.

Architecture:
    JSON SerDe is part of the chain of responsibility pattern for the
    ENCODING chain type. It uses Python's standard json module for
    serialization/deserialization.

Usage:
    Import JSONSerDe directly:
        >>> from pyiv.serde import JSONSerDe
        >>> serde = JSONSerDe()
        >>> data = serde.serialize({"key": "value"})
        >>> result = serde.deserialize(data)

    Or use via chain handler injection:
        >>> from pyiv import ChainType, Config, get_injector
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register_chain_handler(ChainType.ENCODING, "json", JSONSerDe)
        >>> injector = get_injector(MyConfig)
        >>> serde = injector.inject_chain_handler(ChainType.ENCODING, "json")

For other standard Python encodings (base64, pickle, XML, YAML, etc.),
see the pyiv.serde.encodings module.
"""

# JSON SerDe is now in encodings.py
from pyiv.serde.encodings import JSONSerDe

__all__ = ["JSONSerDe"]

