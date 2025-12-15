"""SerDe (Serialize/Deserialize) module for pyiv.

This module provides a SerDe interface and implementations for various
encoding types (JSON, MessagePack, TOML, etc.). The SerDe system integrates
with pyiv's dependency injection to allow type and name-based selection of
serialization implementations.

Architecture:
    - SerDe: Base abstract class for all serialization implementations
    - JSON SerDe implementations: Standard, gRPC-compatible, custom variants
    - DI Integration: Register and inject SerDe instances by type or name

Usage:
    Register SerDe implementations in Config:
        >>> from pyiv import Config, get_injector
        >>> from pyiv.serde import SerDe, JSONSerDe
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         # Register by encoding type
        ...         self.register_serde("json", JSONSerDe)
        ...         # Register by name
        ...         self.register_serde_by_name("json-grpc", JSONSerDe, encoding_type="json")
        ...         # Register multiple instances of same type
        ...         self.register_serde_by_name("json-input", JSONSerDe, encoding_type="json")
        ...         self.register_serde_by_name("json-output", JSONSerDe, encoding_type="json")
        >>> injector = get_injector(MyConfig)
        >>> # Inject by type
        >>> json_serde = injector.inject_serde("json")
        >>> # Inject by name
        >>> grpc_serde = injector.inject_serde_by_name("json-grpc")
"""

from pyiv.serde.base import SerDe
from pyiv.serde.json import JSONSerDe, StandardJSONSerDe, GRPCJSONSerDe

__all__ = [
    "SerDe",
    "JSONSerDe",
    "StandardJSONSerDe",
    "GRPCJSONSerDe",
]

