"""Apply ``LogOptions`` to the stdlib logging hierarchy."""

from __future__ import annotations

import logging
import sys
from typing import Optional

from pyiv.log.factory import abbreviate_logger_name
from pyiv.log.options import LogOptions

_HANDLER_MARK = "_pyiv_log_handler"


class _ShortNameFilter(logging.Filter):
    """Attach abbreviated logger name for formatters."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.shortname = abbreviate_logger_name(record.name)  # type: ignore[attr-defined]
        return True


class _PrefixFilter(logging.Filter):
    def __init__(self, allow: tuple, deny: tuple) -> None:
        super().__init__()
        self._allow = allow
        self._deny = deny

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        if self._deny and any(name == p or name.startswith(p + ".") for p in self._deny):
            return False
        if self._allow:
            return any(name == p or name.startswith(p + ".") for p in self._allow)
        return True


class LogSetup:
    """Configure root logging from ``LogOptions`` (idempotent replace).

    **Why this exists:** CLI ``-v`` / ``--log-level`` should apply once without
    fighting duplicate handlers or hand-rolled ``basicConfig``.

    Example:
        >>> from pyiv.log import LogOptions, LogSetup
        >>> LogSetup().apply(LogOptions(level="INFO", format_style="short"))
    """

    def __init__(self, stream=None) -> None:
        self._stream = stream if stream is not None else sys.stderr

    def apply(self, options: LogOptions) -> None:
        """Replace pyiv-managed root handlers with options-derived config."""
        root = logging.getLogger()
        for handler in list(root.handlers):
            if getattr(handler, _HANDLER_MARK, False):
                root.removeHandler(handler)
                handler.close()

        level_name = options.effective_level()
        level = getattr(logging, level_name, logging.WARNING)
        root.setLevel(level)

        if options.format_style == "long":
            fmt = "%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s"
        else:
            fmt = "%(asctime)s %(levelname)s %(shortname)s %(message)s"

        handler = logging.StreamHandler(self._stream)
        setattr(handler, _HANDLER_MARK, True)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
        handler.addFilter(_ShortNameFilter())
        handler.addFilter(_PrefixFilter(options.allow_prefixes, options.deny_prefixes))
        root.addHandler(handler)

        for name, lvl in options.logger_levels.items():
            logging.getLogger(name).setLevel(getattr(logging, lvl.upper(), logging.WARNING))


class MemoryLogSetup:
    """No-op setup for tests that use ``MemoryLogger`` only.

    **Why this exists:** Avoid attaching handlers when tests inject memory logs.
    """

    def apply(self, options: Optional[LogOptions] = None) -> None:
        return None
