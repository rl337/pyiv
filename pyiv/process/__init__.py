"""Injectable process, environment, and argv surfaces.

**What Problem Does This Solve?**

``subprocess``, ``os.environ``, and ``sys.argv`` are process-global and hard to
isolate in tests. Inject narrow purpose types instead of mocking modules.

Example:
    >>> from pyiv.process import MemoryEnvironment, MemoryProcessRunner
    >>> env = MemoryEnvironment({"PATH": "/bin"})
    >>> env.get("PATH")
    '/bin'
    >>> runner = MemoryProcessRunner()
    >>> runner.script(["echo"], returncode=0, stdout="hi\\n")
    >>> result = runner.run(["echo", "hi"])
    >>> result.stdout
    'hi\\n'
"""

from pyiv.process.argv import Argv, ExitStatus, MemoryArgv, SysArgv
from pyiv.process.environment import Environment, MemoryEnvironment, OsEnvironment
from pyiv.process.runner import (
    CompletedProcess,
    MemoryProcessRunner,
    ProcessRunner,
    RealProcessRunner,
    RunOptions,
)

__all__ = [
    "Environment",
    "OsEnvironment",
    "MemoryEnvironment",
    "ProcessRunner",
    "RealProcessRunner",
    "MemoryProcessRunner",
    "CompletedProcess",
    "RunOptions",
    "Argv",
    "MemoryArgv",
    "SysArgv",
    "ExitStatus",
]
