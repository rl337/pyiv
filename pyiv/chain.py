"""Chain of Responsibility pattern for pyiv.

This module provides a general chain of responsibility system that can be used
for various purposes: encoding, hashing, sorting, etc. Each chain type has its
own interface and implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class ChainType(Enum):
    """Category key for a family of chain-of-responsibility handlers.

    **Why this exists:** SerDe, network clients, and other pluggable handlers
    share the same registration/injection machinery but must not collide.
    ``ChainType`` namespaces those registries (encoding vs network, …).

    Example:
        >>> from pyiv.chain import ChainType
        >>> ChainType.ENCODING.value
        'encoding'
        >>> ChainType.NETWORK_CLIENT.value
        'network_client'
    """

    ENCODING = "encoding"
    HASHING = "hashing"
    SORTING = "sorting"
    NETWORK_CLIENT = "network_client"


class ChainHandler(ABC):
    """Pluggable handler looked up by chain type and handler name/type.

    **Why this exists:** Apps need interchangeable strategies (JSON vs pickle,
    HTTP vs HTTPS) without hard-coding classes at call sites. Register handlers
    on ``Config`` and resolve them with ``inject_chain_handler``.

    Example:
        >>> from pyiv.serde import JSONSerDe
        >>> h: ChainHandler = JSONSerDe()
        >>> h.chain_type is ChainType.ENCODING
        True
        >>> h.handler_type
        'json'
    """

    @property
    @abstractmethod
    def chain_type(self) -> ChainType:
        """Return the chain type this handler belongs to.

        Returns:
            The ChainType enum value
        """
        pass

    @property
    @abstractmethod
    def handler_type(self) -> str:
        """Return the handler type identifier.

        This identifies the specific implementation (e.g., "json", "md5", "quicksort").

        Returns:
            A string identifying the handler type
        """
        pass

    @abstractmethod
    def handle(self, request: Any, **kwargs) -> Any:
        """Handle a request.

        Args:
            request: The request to handle
            **kwargs: Additional keyword arguments

        Returns:
            The result of handling the request
        """
        pass
