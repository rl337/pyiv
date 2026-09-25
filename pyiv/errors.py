"""Injection and creation errors with dependency path context.

**What Problem Does This Solve?**

Guice-style DI graphs fail deep in the tree. A bare ``ValueError`` without the
resolution path makes debugging slow. ``CreationError`` carries the path
(``A -> B -> C``) and optional nested causes so failures are actionable.

**Real-World Use Cases:**

- Fail-fast warmup in ``Stage.PRODUCTION`` with aggregated messages
- Circular dependency reports with the cycle path
- Missing bindings that name the requesting type

Usage Examples:

    >>> from pyiv.errors import CreationError
    >>> err = CreationError("No binding for Database", path=["App", "Service", "Database"])
    >>> "App -> Service -> Database" in str(err)
    True
"""

from typing import List, Optional, Sequence


class CreationError(Exception):
    """Raised when the injector cannot create or resolve a dependency.

    **Why this exists:** Deep graphs fail far from the call site. This error
    carries the resolution path and optional nested causes so you can see
    ``App -> Service -> Database`` instead of a bare ``ValueError``.

    Args:
        message: Human-readable failure reason
        path: Resolution path from the root request to the failing type
        causes: Nested failures (e.g. eager singleton warmup aggregation)

    Example:
        >>> err = CreationError("No binding", path=["Service", "Database"])
        >>> "Service -> Database" in str(err)
        True
    """

    def __init__(
        self,
        message: str,
        *,
        path: Optional[Sequence[str]] = None,
        causes: Optional[Sequence[BaseException]] = None,
    ):
        self.message = message
        self.path: List[str] = list(path) if path else []
        self.causes: List[BaseException] = list(causes) if causes else []
        super().__init__(self._format())

    def _format(self) -> str:
        parts = [self.message]
        if self.path:
            parts.append(f"Path: {' -> '.join(self.path)}")
        if self.causes:
            for i, cause in enumerate(self.causes, 1):
                parts.append(f"Cause {i}: {cause}")
        return "\n".join(parts)


def type_name(obj: object) -> str:
    """Return a short display name for a type, key, or other binding target."""
    if isinstance(obj, type):
        return obj.__name__
    name = getattr(obj, "__name__", None)
    if isinstance(name, str):
        return name
    return repr(obj)
