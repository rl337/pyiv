"""Argparse helpers for logging flags and Command integration."""

from __future__ import annotations

import argparse
from typing import Any

from pyiv.log.options import LogOptions


def add_logging_args(parser: argparse.ArgumentParser) -> None:
    """Add ``-v`` / ``-q`` / ``--log-level`` / ``--log-format`` to ``parser``.

    **Why this exists:** Commands share one CLI surface for log configuration.

    Example:
        >>> import argparse
        >>> p = argparse.ArgumentParser()
        >>> add_logging_args(p)
        >>> ns = p.parse_args(["-vv", "--log-format", "long"])
        >>> ns.verbose
        2
    """
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v INFO, -vv DEBUG)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only log errors",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        help="Base log level when not using -v/-q (default: WARNING)",
    )
    parser.add_argument(
        "--log-format",
        choices=("short", "long"),
        default="short",
        dest="log_format",
        help="Log line format (short abbreviates logger names)",
    )


def log_options_from_args(args: Any) -> LogOptions:
    """Build ``LogOptions`` from an argparse namespace (or similar).

    Example:
        >>> ns = argparse.Namespace(verbose=1, quiet=False, log_level="WARNING", log_format="short")
        >>> log_options_from_args(ns).effective_level()
        'INFO'
    """
    return LogOptions(
        level=getattr(args, "log_level", "WARNING"),
        verbose=int(getattr(args, "verbose", 0) or 0),
        quiet=bool(getattr(args, "quiet", False)),
        format_style=getattr(args, "log_format", "short"),
    )
