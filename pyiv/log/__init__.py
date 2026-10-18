"""Injectable logging over stdlib ``logging`` (configure + wrap, not fork).

**What Problem Does This Solve?**

Stdlib logging is powerful but awkward to wire from the CLI and hard to assert
in tests. ``LogSetup`` + ``LogOptions`` apply opinionated formatting;
``MemoryLogger`` captures records without handler residue.

Keep ``pyiv.console`` for human-facing I/O; use ``Logger`` for diagnostics.

Example:
    >>> from pyiv.log import LogOptions, LogSetup, LoggerFactory, StdlibLoggerFactory
    >>> LogSetup().apply(LogOptions(level="INFO"))
    >>> log = StdlibLoggerFactory().get("demo")
    >>> log.info("hello")
"""

from pyiv.log.cli import add_logging_args, log_options_from_args
from pyiv.log.factory import LoggerFactory, MemoryLoggerFactory, StdlibLoggerFactory
from pyiv.log.logger import Logger, LogRecord, MemoryLogger, StdlibLogger
from pyiv.log.options import LogOptions
from pyiv.log.setup import LogSetup, MemoryLogSetup

__all__ = [
    "Logger",
    "StdlibLogger",
    "MemoryLogger",
    "LogRecord",
    "LoggerFactory",
    "StdlibLoggerFactory",
    "MemoryLoggerFactory",
    "LogOptions",
    "LogSetup",
    "MemoryLogSetup",
    "add_logging_args",
    "log_options_from_args",
]
