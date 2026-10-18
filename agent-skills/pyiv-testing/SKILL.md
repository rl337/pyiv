---
name: pyiv-testing
description: >-
  Tests pyiv-based apps with injectable doubles instead of monkeypatching
  time, filesystem, env, subprocess, logging, or HTTP. Use when writing unit
  tests, pytest fixtures, or TestConfig overlays for code that uses pyiv.
---

# Test with pyiv doubles

Do not mock `open`, `time`, `os.environ`, `subprocess`, `logging.getLogger`,
or `sys.stdout` when pyiv provides an injectable double.

## Bind doubles in a test Config

```python
from pyiv import Config, get_injector, override
from pyiv import (
    Clock,
    SyntheticClock,
    Filesystem,
    MemoryFilesystem,
    Console,
    MemoryConsole,
    Environment,
    MemoryEnvironment,
    LoggerFactory,
    MemoryLoggerFactory,
)

class TestConfig(Config):
    def configure(self):
        self.register(Clock, lambda: SyntheticClock(start_time=100.0), singleton=True)
        self.register(Filesystem, MemoryFilesystem)
        self.register(Console, MemoryConsole)
        self.register(Environment, MemoryEnvironment)
        self.register(LoggerFactory, MemoryLoggerFactory)

# Or overlay production:
# get_injector(override(ProdConfig).with_(TestConfig))
```

## What to swap

| Need | Bind |
| --- | --- |
| Freeze/advance time | `Clock` → `SyntheticClock` |
| No disk I/O | `Filesystem` → `MemoryFilesystem` (mount zip/tar/`/proc` via `MountFilesystem`) |
| Capture prints | `Console` → `MemoryConsole` |
| Fixed calendar time | `DateTimeService` → `MockDateTimeService` |
| Env without residue | `Environment` → `MemoryEnvironment` |
| Scripted subprocess | `ProcessRunner` → `MemoryProcessRunner` |
| Assert log lines | `LoggerFactory` → `MemoryLoggerFactory` |
| Deterministic tokens | `Entropy` → `SyntheticEntropy` |
| Fixed digests | `Hasher` → `SyntheticHasher` |
| HTTP without network | `HttpClient` → `MemoryHttpClient` |

## Do

1. Keep production classes; only replace world edges.
2. Advance `SyntheticClock` instead of sleeping for coordination.
3. Prefer `MemoryFilesystem` + mounts over `pyfakefs` when the app already
   depends on `Filesystem`.

## Don't

1. Leave files, env mutations, or logging handlers as process residue after tests.
2. Hit the network in unit tests when `MemoryHttpClient` suffices.

Guide: https://rl337.org/pyiv/guide/testing.html
