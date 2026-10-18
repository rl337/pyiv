"""Frozen logging options (CLI / Settings knobs)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class LogOptions:
    """Configuration for ``LogSetup.apply``.

    **Why this exists:** CLI flags and host Settings need a boring frozen bag —
    not ``dictConfig`` sprawl — without a pydantic dependency.

    Example:
        >>> opts = LogOptions(level="DEBUG", verbose=1)
        >>> opts.as_dict()["level"]
        'DEBUG'
    """

    level: str = "WARNING"
    verbose: int = 0
    quiet: bool = False
    format_style: str = "short"  # short | long
    allow_prefixes: Tuple[str, ...] = ()
    deny_prefixes: Tuple[str, ...] = ()
    logger_levels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "allow_prefixes", tuple(self.allow_prefixes))
        object.__setattr__(self, "deny_prefixes", tuple(self.deny_prefixes))
        object.__setattr__(self, "logger_levels", dict(self.logger_levels))

    def effective_level(self) -> str:
        """Resolve level from quiet / verbose / explicit level."""
        if self.quiet:
            return "ERROR"
        if self.verbose >= 2:
            return "DEBUG"
        if self.verbose == 1:
            return "INFO"
        return self.level.upper()

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LogOptions":
        return cls(
            level=str(data.get("level", "WARNING")),
            verbose=int(data.get("verbose", 0)),
            quiet=bool(data.get("quiet", False)),
            format_style=str(data.get("format_style", "short")),
            allow_prefixes=tuple(data.get("allow_prefixes") or ()),
            deny_prefixes=tuple(data.get("deny_prefixes") or ()),
            logger_levels=dict(data.get("logger_levels") or {}),
        )
