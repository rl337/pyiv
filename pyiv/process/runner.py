"""Injectable subprocess runner."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union


@dataclass(frozen=True)
class RunOptions:
    """Options for a single ``ProcessRunner.run`` call.

    **Why this exists:** Frozen knob for Settings nesting without pydantic.

    Example:
        >>> RunOptions(timeout=1.0).as_dict()["timeout"]
        1.0
    """

    cwd: Optional[str] = None
    env: Optional[Mapping[str, str]] = None
    timeout: Optional[float] = None
    check: bool = False
    text: bool = True

    def __post_init__(self) -> None:
        if self.env is not None:
            object.__setattr__(self, "env", dict(self.env))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompletedProcess:
    """Result of a process run (stdlib-shaped, frozen).

    **Why this exists:** Boring DTO for assertions and Settings round-trip.

    Example:
        >>> CompletedProcess(["true"], 0).returncode
        0
    """

    args: Sequence[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(self.args))


class ProcessRunner(ABC):
    """Injectable subprocess runner.

    **Why this exists:** Call sites that use ``subprocess.run`` are hard to
    unit-test. Inject ``ProcessRunner`` and bind ``MemoryProcessRunner``.

    Example:
        >>> from pyiv.process import MemoryProcessRunner
        >>> runner: ProcessRunner = MemoryProcessRunner()
        >>> runner.script(["true"], returncode=0)
        >>> runner.run(["true"]).returncode
        0
    """

    @abstractmethod
    def run(
        self,
        argv: Sequence[str],
        *,
        options: Optional[RunOptions] = None,
    ) -> CompletedProcess:
        """Run ``argv`` and return a completed process result."""


class RealProcessRunner(ProcessRunner):
    """Process runner backed by ``subprocess.run``.

    **Why this exists:** Production binding for real child processes.
    """

    def run(
        self,
        argv: Sequence[str],
        *,
        options: Optional[RunOptions] = None,
    ) -> CompletedProcess:
        opts = options or RunOptions()
        completed = subprocess.run(
            list(argv),
            cwd=opts.cwd,
            env=dict(opts.env) if opts.env is not None else None,
            timeout=opts.timeout,
            check=opts.check,
            text=opts.text,
            capture_output=True,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if not opts.text:
            stdout = (
                stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else stdout
            )
            stderr = (
                stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else stderr
            )
        return CompletedProcess(
            args=list(argv),
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
        )


class MemoryProcessRunner(ProcessRunner):
    """Scripted process runner for tests.

    **Why this exists:** Assert argv and return canned results without spawning.

    Example:
        >>> runner = MemoryProcessRunner()
        >>> runner.script(["echo", "hi"], returncode=0, stdout="hi\\n")
        >>> runner.run(["echo", "hi"]).stdout
        'hi\\n'
    """

    def __init__(self) -> None:
        self.calls: List[Sequence[str]] = []
        self._scripts: List[tuple] = []
        self._default: Optional[Callable[[Sequence[str]], CompletedProcess]] = None

    def script(
        self,
        argv_prefix: Sequence[str],
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Register a canned result when argv starts with ``argv_prefix``."""
        prefix = tuple(argv_prefix)

        def handler(argv: Sequence[str]) -> CompletedProcess:
            return CompletedProcess(argv, returncode, stdout, stderr)

        self._scripts.append((prefix, handler))

    def set_default(self, handler: Callable[[Sequence[str]], CompletedProcess]) -> None:
        self._default = handler

    def run(
        self,
        argv: Sequence[str],
        *,
        options: Optional[RunOptions] = None,
    ) -> CompletedProcess:
        self.calls.append(tuple(argv))
        for prefix, handler in self._scripts:
            if tuple(argv[: len(prefix)]) == prefix:
                return handler(argv)
        if self._default is not None:
            return self._default(argv)
        return CompletedProcess(argv, 0, "", "")
