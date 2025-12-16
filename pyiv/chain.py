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
    """Types of chain of responsibility handlers.

    Each chain type represents a different category of handlers:
    - ENCODING: Serialization/deserialization (SerDe)
    - HASHING: Hash function implementations
    - SORTING: Sorting algorithm implementations
    - etc.
    """

    ENCODING = "encoding"
    HASHING = "hashing"
    SORTING = "sorting"


class ChainHandler(ABC):
    """Abstract base class for chain of responsibility handlers.

    Chain handlers process requests in a chain. Each handler can either:
    - Handle the request and return a result
    - Pass the request to the next handler in the chain
    - Reject the request

    Subclasses must implement:
        - chain_type: The type of chain this handler belongs to
        - handler_type: The specific handler type identifier (e.g., "json", "md5", "quicksort")
        - handle(): Process the request
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
