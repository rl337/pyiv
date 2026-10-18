"""Injectable argv and exit status for CLI tests."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class ExitStatus:
    """Recorded process exit code.

    **Why this exists:** Capture ``sys.exit`` intent without terminating tests.

    Example:
        >>> ExitStatus(2).code
        2
    """

    code: int = 0


class Argv(ABC):
    """Injectable program arguments and exit reporting.

    **Why this exists:** CLI code that reads ``sys.argv`` or calls ``sys.exit``
    is awkward in unit tests. Inject ``Argv`` instead.

    Example:
        >>> from pyiv.process import MemoryArgv
        >>> argv: Argv = MemoryArgv(["prog", "--verbose"])
        >>> list(argv.args)
        ['prog', '--verbose']
    """

    @property
    @abstractmethod
    def args(self) -> Sequence[str]:
        """Program arguments including argv[0]."""

    @abstractmethod
    def exit(self, code: int = 0) -> None:
        """Request process exit with ``code``."""


class MemoryArgv(Argv):
    """In-memory argv / exit capture for tests.

    **Why this exists:** Drive CLI parsing without touching ``sys``.

    Example:
        >>> a = MemoryArgv(["tool", "-v"])
        >>> a.exit(1)
        >>> a.exit_status.code
        1
    """

    def __init__(self, args: Optional[Sequence[str]] = None) -> None:
        self._args: List[str] = list(args if args is not None else ["prog"])
        self.exit_status = ExitStatus(0)
        self.exited = False

    @property
    def args(self) -> Sequence[str]:
        return tuple(self._args)

    def exit(self, code: int = 0) -> None:
        self.exit_status = ExitStatus(code)
        self.exited = True


class SysArgv(Argv):
    """Argv backed by ``sys.argv`` / ``sys.exit``.

    **Why this exists:** Production binding for real CLI entrypoints.
    """

    @property
    def args(self) -> Sequence[str]:
        return tuple(sys.argv)

    def exit(self, code: int = 0) -> None:
        raise SystemExit(code)
