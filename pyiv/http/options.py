"""HTTP client option bags (frozen, pydantic-friendly shapes)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class HttpClientOptions:
    """Scalar configuration for HTTP clients.

    **Why this exists:** Host apps (including pydantic ``BaseSettings``) need a
    boring frozen options bag to nest or round-trip without pyiv depending on
    pydantic. Keep ``session`` and other injectables off this type.

    Example:
        >>> from pyiv.http.options import HttpClientOptions
        >>> opts = HttpClientOptions(base_url="https://api.example/", timeout=5.0)
        >>> opts.as_dict()["timeout"]
        5.0
        >>> HttpClientOptions.from_dict(opts.as_dict()).base_url
        'https://api.example/'
    """

    base_url: Optional[str] = None
    headers: Mapping[str, str] = field(default_factory=dict)
    timeout: Optional[float] = None
    https_only: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", dict(self.headers))

    def as_dict(self) -> Dict[str, Any]:
        """Return a plain dict suitable for Settings dump/load."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HttpClientOptions":
        """Build options from a mapping (unknown keys ignored)."""
        return cls(
            base_url=data.get("base_url"),
            headers=dict(data.get("headers") or {}),
            timeout=data.get("timeout"),
            https_only=bool(data.get("https_only", False)),
        )
