"""SerDe (Serialize/Deserialize) module for pyiv.

This module provides SerDe implementations as part of the chain of responsibility
pattern. SerDe is a chain handler for the ENCODING chain type, providing
serialization/deserialization for various encoding formats available in Python's
standard library.

Architecture:
    - SerDe: Base abstract class extending ChainHandler for ENCODING chain type
    - Standard encodings: JSON, Base64, XML, Pickle, NoOp
    - YAML: ``pyiv-common`` (``from pyiv_common.serde import YAMLSerDe``)
    - DI Integration: Register and inject SerDe instances via chain system

Usage:
    Register SerDe implementations in Config:
        >>> from pyiv import Config, get_injector, ChainType
        >>> from pyiv.serde import JSONSerDe, PickleSerDe
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # Register by handler type
        ...         self.register_chain_handler(ChainType.ENCODING, "json", JSONSerDe)
        ...         # Register by name (allows multiple implementations)
        ...         self.register_chain_handler_by_name(
        ...             ChainType.ENCODING, "json-input", JSONSerDe, handler_type="json"
        ...         )
        ...         # Register default (no-op or pickle)
        ...         self.register_chain_handler(ChainType.ENCODING, "default", PickleSerDe)
        >>> injector = get_injector(MyConfig)
        >>> json_serde = injector.inject_chain_handler(ChainType.ENCODING, "json")
        >>> json_serde.handler_type
        'json'
        >>> input_serde = injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-input")
        >>> input_serde.handler_type
        'json'
"""

from pyiv.serde.base import SerDe
from pyiv.serde.encodings import Base64SerDe, JSONSerDe, NoOpSerDe, PickleSerDe, XMLSerDe

__all__ = [
    "SerDe",
    "JSONSerDe",
    "Base64SerDe",
    "XMLSerDe",
    "PickleSerDe",
    "NoOpSerDe",
]


def __getattr__(name: str):
    """Compatibility shim: YAMLSerDe moved to pyiv-common.

    ``from pyiv.serde import YAMLSerDe`` still works if ``pyiv-common`` is
    installed. The name is not in ``__all__`` and is not documented as core.
    """
    if name == "YAMLSerDe":
        try:
            from pyiv_common.serde import YAMLSerDe
        except ImportError as exc:
            raise ImportError(
                "YAMLSerDe lives in pyiv-common. Install it with: pip install pyiv-common"
            ) from exc
        return YAMLSerDe
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
