# Stdlib injectable surfaces (use-case catalog)

Living inventory of Python standard-library capabilities mapped to **use-case**
injectable packages in pyiv—not 1:1 wrappers of `os` / `sys` / `io` module names.

Status values:

- **shipped** — public API exists with Real + test double (or equivalent)
- **gap** — planned / in progress
- **wont** — deliberately not wrapped (see Won’t wrap)

## Surface template

Each use-case package should ship: narrow Protocol/ABC, Real\* adapter (instance
state only), Memory/Synthetic\* double (no system residue), optional composites
(mounts, archives-as-FS), file-likes where I/O applies, and doctest-backed docs.
Option bags are frozen dataclasses with boring field types (pydantic-friendly
without a pydantic dependency). See `.cursor/skills/public-types/SKILL.md`.

## Catalog by use case

| Use case package | Stdlib sources (concepts) | Types | Status |
| --- | --- | --- | --- |
| `pyiv.files` | `open`, `pathlib`, file bits of `os`/`shutil`, `tempfile`, `zipfile`/`tarfile` as trees | `Filesystem`, `RealFilesystem`, `MemoryFilesystem`, `MountFilesystem`, `ZipFilesystem`, `TarFilesystem`, `MappingFilesystem` | shipped |
| `pyiv.time` | `time`, `datetime`, sched-style callbacks | `Clock`, `Timer`, `DateTimeService` (+ Real/Synthetic/Mock) | shipped |
| `pyiv.console` | `sys.stdout`/`stdin`, TTY/PTY | `Console`, Real/Memory/File/PTY/Mock | shipped |
| `pyiv.log` | `logging` (configure + wrap, not fork) | `Logger`, `LoggerFactory`, `LogSetup`, `LogOptions`, Memory\* | shipped |
| `pyiv.process` | `subprocess`, `os.environ`, `sys.argv`/`sys.exit` | `Environment`, `ProcessRunner`, `Argv` | shipped |
| `pyiv.http` | `urllib` | `HttpClient`, `AsyncHttpClient`, Memory\* | shipped |
| `pyiv.serde` | `json`, `pickle`, `xml`, `base64` facades | `SerDe` + encodings | shipped |
| `pyiv.entropy` | `random`, `secrets` | `Entropy`, Real/Synthetic | shipped |
| `pyiv.hashing` | `hashlib`, `hmac` | `Hasher`, Real/Synthetic | shipped |

Legacy top-level modules (`pyiv.filesystem`, `pyiv.clock`, `pyiv.datetime_service`)
re-export from use-case packages for one major cycle.

## Stdlib module → bucket

| Stdlib | Bucket | Notes |
| --- | --- | --- |
| `io`, `pathlib`, `os` (paths/files), `shutil`, `tempfile` | `pyiv.files` | Not a god `Os` façade |
| `zipfile`, `tarfile` | `pyiv.files` | Archives as `Filesystem` trees |
| `time`, `datetime` | `pyiv.time` | |
| `sys` (stdio) | `pyiv.console` | |
| `sys` (argv/exit) | `pyiv.process` | |
| `os.environ` | `pyiv.process` | Injectable `Environment` |
| `subprocess`, `signal` | `pyiv.process` | Signals deferred until a consumer needs them |
| `logging` | `pyiv.log` | Configure stdlib hierarchy; Console ≠ Logger |
| `urllib` | `pyiv.http` | |
| `json` / `pickle` / `xml.etree` / `base64` | `pyiv.serde` | |
| `random` / `secrets` | `pyiv.entropy` | |
| `hashlib` / `hmac` | `pyiv.hashing` | |

## Won’t wrap

- **math, collections, itertools, functools, operator** — pure helpers; no I/O or process edge
- **typing, dataclasses, enum, abc** — language tooling
- **asyncio event-loop ownership** — note gaps; no fake loop in early phases
- **threading / multiprocessing primitives** — prefer real sync; don’t inject Lock by default
- **ctypes, importlib machinery, gc, inspect** — too low-level / reflective
- **God objects named `Sys`, `Os`, `Io`** — split by use case instead
- **Second logging backend** that bypasses stdlib `logging` (breaks library interop)
- **DB/S3/Postgres filesystems in core** — implement `Filesystem` externally; use `MountFilesystem`

## Third-party displacements

| Convenience / test helper | Prefer |
| --- | --- |
| `freezegun` / time freezers | `SyntheticClock` / `MockDateTimeService` |
| `pyfakefs` | `MemoryFilesystem` + `MountFilesystem` |
| `responses` / `httpretty` | `MemoryHttpClient` |
| Hand-rolled `logging.basicConfig` / dictConfig CLI glue | `pyiv.log` `LogSetup` + `add_logging_args` |
| Ad-hoc `os.environ` mutation in tests | `MemoryEnvironment` |
| Ad-hoc `subprocess` mocks | `MemoryProcessRunner` |

## Design rules (reminder)

1. Instances over module globals / monkeypatches
2. One job per injectable type
3. Narrow purpose APIs over full stdlib module surfaces
4. Option bags: frozen dataclasses; services: Protocol/ABC
5. Core stays stdlib-only (see package-boundaries skill)
