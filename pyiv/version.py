"""Version sources, parsers, and version-conditioned bindings.

Select among multiple implementations of the same interface based on a
**named version domain** — installed package versions, the running Python
interpreter, or any host-defined domain (OS release, wire protocol, …).

**What Problem Does This Solve?**

Hosts inherit transitive dependency versions they do not pin directly. Adapter
libraries need to register several implementations and let the injector pick
the one compatible with the environment. The same mechanism covers interpreter
specialization (``async`` APIs that differ by Python version) and non-Python
domains when the host supplies a :class:`VersionSource` and a named
:class:`VersionParser`.

**Real-World Use Cases:**

- Pick an HTTP adapter compatible with the installed ``requests`` distribution
- Prefer an optional accelerator (``cjson``, ``orjson``, …) when installed
  via ``for_package_present`` / ``for_package_absent`` (or present + fallback)
- Use ``TaskGroup``-based runners only on Python 3.11+
- Bind filesystem helpers based on the host OS release (custom parser)
- Tests bind a :class:`FixedPythonVersionProvider` (or a fixed
  :class:`MapVersionSource`) instead of monkeypatching ``sys`` /
  ``importlib.metadata``

Architecture:

- :class:`VersionSource` — obtains the current version string for a domain
- :class:`VersionParser` — ``compatible`` / ``less`` / ``greater`` predicates
- Named parser registry — ``\"PEP440\"`` defaults to
  :class:`~pyiv.pep440.Pep440VersionParser`; hosts register others by name
- :class:`PythonVersionProvider` — injectable interpreter version (sys or fixed)
- Reserved presence/absence specifiers — :data:`PACKAGE_PRESENT` (``\"*\"``)
  and :data:`PACKAGE_ABSENT` (``\"!\"``)
- Fluent Binder: ``.for_version`` / ``.for_package_version`` /
  ``.for_package_present`` / ``.for_package_absent`` /
  ``.for_python_version`` register **candidates**; the injector selects one
  when the environment is stable (at injector construction)

Usage Examples:

    Python interpreter specialization (inject a test provider)::

        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import FixedPythonVersionProvider, PythonVersionProvider
        >>> class Runner:
        ...     kind = "base"
        >>> class LegacyRunner(Runner):
        ...     kind = "legacy"
        >>> class ModernRunner(Runner):
        ...     kind = "modern"
        >>> class RunnerConfig(Config):
        ...     def configure(self):
        ...         binder = self.get_binder()
        ...         binder.bind(PythonVersionProvider).to_instance(
        ...             FixedPythonVersionProvider("3.10.12")
        ...         )
        ...         binder.bind(Runner).to(LegacyRunner).for_python_version("<3.11")
        ...         binder.bind(Runner).to(ModernRunner).for_python_version(">=3.11")
        >>> inj = get_injector(RunnerConfig)
        >>> inj.inject(Runner).kind
        'legacy'
        >>> inj.inject(PythonVersionProvider).get_version()
        '3.10.12'

    Optional package present / absent (accelerator vs stdlib)::

        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import MapVersionSource, package_version_domain
        >>> class Encoder:
        ...     kind = "base"
        >>> class FastEncoder(Encoder):
        ...     kind = "fast"
        >>> class StdEncoder(Encoder):
        ...     kind = "std"
        >>> domain = package_version_domain("cjson")
        >>> class PresentConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         # Tests: simulate an installed distribution without installing it.
        ...         b.version_source(domain, MapVersionSource({domain: "1.0.0"}))
        ...         b.bind(Encoder).to(FastEncoder).for_package_present("cjson")
        ...         b.bind(Encoder).to(StdEncoder).for_package_absent("cjson")
        >>> get_injector(PresentConfig).inject(Encoder).kind
        'fast'
        >>> class AbsentConfig(Config):
        ...     def configure(self):
        ...         b = self.get_binder()
        ...         missing = "pyiv-definitely-not-installed-xyz"
        ...         b.bind(Encoder).to(FastEncoder).for_package_present(missing)
        ...         b.bind(Encoder).to(StdEncoder).for_package_absent(missing)
        >>> get_injector(AbsentConfig).inject(Encoder).kind
        'std'

    Custom domain with a named parser::

        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import MapVersionSource
        >>> class FsTool:
        ...     name = "base"
        >>> class AlpineFs(FsTool):
        ...     name = "alpine"
        >>> class DebFs(FsTool):
        ...     name = "deb"
        >>> class AlpineVersionParser:
        ...     '''Treat dotted release numbers as integer tuples.'''
        ...     def is_version_compatible(self, version, specifier):
        ...         assert specifier.startswith(">=")
        ...         return self._tuple(version) >= self._tuple(specifier[2:])
        ...     def is_version_less(self, a, b):
        ...         return self._tuple(a) < self._tuple(b)
        ...     def is_version_greater(self, a, b):
        ...         return self._tuple(a) > self._tuple(b)
        ...     def _tuple(self, s):
        ...         return tuple(int(p) for p in s.split("."))
        >>> class OsConfig(Config):
        ...     def configure(self):
        ...         binder = self.get_binder()
        ...         binder.version_parser("alpine-release", AlpineVersionParser())
        ...         binder.version_source("alpine", MapVersionSource({"alpine": "3.19.0"}))
        ...         binder.use_version_parser("alpine", "alpine-release")
        ...         binder.bind(FsTool).to(AlpineFs).for_version("alpine", ">=3.18")
        ...         binder.bind(FsTool).to(DebFs).for_version("alpine", ">=99")
        >>> get_injector(OsConfig).inject(FsTool).name
        'alpine'
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Protocol, Type, runtime_checkable

from pyiv.provider import Provider
from pyiv.scope import Scope

if TYPE_CHECKING:
    from pyiv.config import Config

# Built-in domain / parser names.
PYTHON_VERSION_DOMAIN = "python"
PEP440 = "PEP440"
PACKAGE_PRESENT = "*"
"""Reserved specifier: match when a :class:`VersionSource` returns any version.

Not a PEP 440 string — injector selection short-circuits before the parser.
Used by ``binder.bind(...).for_package_present(...)`` and
``for_package_version(distribution, PACKAGE_PRESENT)``. See
:func:`is_package_present_specifier` and the module Usage Examples.
"""

PACKAGE_ABSENT = "!"
"""Reserved specifier: match when a :class:`VersionSource` returns ``None``.

Used by ``binder.bind(...).for_package_absent(...)`` and
``for_package_version(distribution, PACKAGE_ABSENT)`` when the distribution
is not installed (or the test :class:`MapVersionSource` has no entry). See
:func:`is_package_absent_specifier` and the module Usage Examples.
"""


def package_version_domain(distribution: str) -> str:
    """Return the version-domain key for an installed distribution name.

    ``for_package_version`` / ``for_package_present`` / ``for_package_absent``
    register sources under ``package:<distribution>``. Tests override that
    domain with a :class:`MapVersionSource`.

    Example:
        >>> from pyiv.version import package_version_domain
        >>> package_version_domain("requests")
        'package:requests'
    """
    return f"package:{distribution}"


def is_package_present_specifier(specifier: str) -> bool:
    """Return True if ``specifier`` means “any installed version” (presence).

    **Why this exists:** Selection and hosts need a stable check for the
    reserved :data:`PACKAGE_PRESENT` token without hard-coding ``\"*\"``.

    Example:
        >>> from pyiv.version import PACKAGE_PRESENT, is_package_present_specifier
        >>> is_package_present_specifier(PACKAGE_PRESENT)
        True
        >>> is_package_present_specifier(">=1.0")
        False
    """
    return specifier == PACKAGE_PRESENT


def is_package_absent_specifier(specifier: str) -> bool:
    """Return True if ``specifier`` means “distribution not installed”.

    **Why this exists:** Parallel to :func:`is_package_present_specifier` for
    the reserved :data:`PACKAGE_ABSENT` token.

    Example:
        >>> from pyiv.version import PACKAGE_ABSENT, is_package_absent_specifier
        >>> is_package_absent_specifier(PACKAGE_ABSENT)
        True
        >>> is_package_absent_specifier("*")
        False
    """
    return specifier == PACKAGE_ABSENT


class InvalidVersion(ValueError):
    """Base error for :class:`VersionParser` parse and match failures.

    **Why this exists:** Call sites and the injector need one exception type
    for "this version string / specifier is unusable," regardless of whether
    the active parser is PEP 440, an OS-release grammar, or a host-defined
    schema epoch. Custom parsers should raise this class or a subclass.

    Example:
        >>> from pyiv.version import InvalidVersion
        >>> raise InvalidVersion("not a version")
        Traceback (most recent call last):
        ...
        pyiv.version.InvalidVersion: not a version
    """


class InvalidSpecifier(InvalidVersion):
    """Raised when a version constraint / specifier string is invalid.

    **Why this exists:** Distinguishes bad constraints (``>>>>1.0``) from bad
    version strings while remaining catchable as :class:`InvalidVersion`.

    Example:
        >>> from pyiv.version import InvalidSpecifier, InvalidVersion
        >>> issubclass(InvalidSpecifier, InvalidVersion)
        True
    """


def default_version_parsers() -> Dict[str, "VersionParser"]:
    """Return the built-in named parser map (``PEP440`` → Pep440VersionParser)."""
    from pyiv.pep440 import Pep440VersionParser

    return {PEP440: Pep440VersionParser()}


__all__ = [
    "InvalidVersion",
    "InvalidSpecifier",
    "VersionParser",
    "VersionSource",
    "Pep440VersionParser",
    "PackageVersionSource",
    "PythonVersionProvider",
    "SysPythonVersionProvider",
    "FixedPythonVersionProvider",
    "PythonVersionSource",
    "MapVersionSource",
    "VersionBindingCandidate",
    "PYTHON_VERSION_DOMAIN",
    "PEP440",
    "PACKAGE_PRESENT",
    "PACKAGE_ABSENT",
    "package_version_domain",
    "is_package_present_specifier",
    "is_package_absent_specifier",
    "default_version_parsers",
]


@runtime_checkable
class VersionParser(Protocol):
    """Parses and matches version strings for a named grammar.

    **Why this exists:** Python package and interpreter versions follow
    :pep:`440`, but hosts often condition bindings on OS releases, wire
    protocols, or schema epochs that do not. Implement this protocol, register
    it with :meth:`pyiv.binder.Binder.version_parser` under a name, and point
    domains at that name with :meth:`pyiv.binder.Binder.use_version_parser`.
    Raise :class:`InvalidVersion` (or a subclass) on unusable input.

    Example:
        >>> from pyiv.pep440 import Pep440VersionParser
        >>> p = Pep440VersionParser()
        >>> p.is_version_compatible("2.31.0", ">=2.30,<3")
        True
        >>> p.is_version_less("1.0", "2.0")
        True
        >>> p.is_version_greater("2.0", "1.0")
        True
    """

    def is_version_compatible(self, version: str, specifier: str) -> bool:
        """Return True if ``version`` satisfies ``specifier`` for this grammar.

        Raises:
            InvalidVersion: If ``version`` or ``specifier`` cannot be parsed.
        """
        ...

    def is_version_less(self, a: str, b: str) -> bool:
        """Return True if ``a`` is strictly less than ``b``.

        Raises:
            InvalidVersion: If either string cannot be parsed.
        """
        ...

    def is_version_greater(self, a: str, b: str) -> bool:
        """Return True if ``a`` is strictly greater than ``b``.

        Raises:
            InvalidVersion: If either string cannot be parsed.
        """
        ...


@runtime_checkable
class VersionSource(Protocol):
    """Provides the current version string for a named domain.

    **Why this exists:** Selection must read *environment* state (installed
    distribution, interpreter, host OS) without baking discovery into the
    binder. Implement this for custom domains, or use
    :class:`MapVersionSource` in tests.

    Example:
        >>> from pyiv.version import MapVersionSource
        >>> src = MapVersionSource({"alpine": "3.19.0"})
        >>> src.get_version()
        '3.19.0'
    """

    def get_version(self) -> Optional[str]:
        """Return the current version, or ``None`` if absent / unknown."""
        ...


class PackageVersionSource:
    """Read an installed distribution version via ``importlib.metadata``.

    **Why this exists:** ``for_package_version``, ``for_package_present``, and
    ``for_package_absent`` need the **distribution** name (as on PyPI), which
    is not always the import package name. This source never imports the
    library — it only consults packaging metadata. ``None`` means absent and
    is what ``for_package_absent`` matches on.

    Example:
        >>> from pyiv.version import PackageVersionSource
        >>> # ``pyiv`` itself is installed in the test / docs environment
        >>> ver = PackageVersionSource("pyiv").get_version()
        >>> ver is None or len(ver.split(".")) >= 2
        True
        >>> PackageVersionSource("pyiv-definitely-not-installed-xyz").get_version() is None
        True
    """

    def __init__(self, distribution: str) -> None:
        """
        Args:
            distribution: Distribution name (``importlib.metadata`` name).
        """
        self.distribution = distribution

    def get_version(self) -> Optional[str]:
        """Return the installed version, or ``None`` if the dist is absent."""
        try:
            from importlib import metadata
        except ImportError:  # pragma: no cover - Python <3.8
            import importlib_metadata as metadata  # type: ignore

        try:
            return metadata.version(self.distribution)
        except metadata.PackageNotFoundError:
            return None


class PythonVersionProvider(ABC):
    """Injectable source of the running (or simulated) Python version.

    **Why this exists:** ``for_python_version`` and application code that
    branches on the interpreter must not hard-code ``sys.version_info``. Bind
    :class:`SysPythonVersionProvider` in production and
    :class:`FixedPythonVersionProvider` in tests so the same graph can be
    exercised under 3.8, 3.10, 3.11, etc.

    Example:
        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import FixedPythonVersionProvider, PythonVersionProvider
        >>> class C(Config):
        ...     def configure(self):
        ...         self.get_binder().bind(PythonVersionProvider).to_instance(
        ...             FixedPythonVersionProvider("3.11.0")
        ...         )
        >>> get_injector(C).inject(PythonVersionProvider).get_version()
        '3.11.0'
    """

    @abstractmethod
    def get_version(self) -> str:
        """Return the interpreter version as a PEP 440 string (e.g. ``3.11.5``)."""


class SysPythonVersionProvider(PythonVersionProvider):
    """Production :class:`PythonVersionProvider` backed by ``sys.version_info``.

    **Why this exists:** Default for ``for_python_version`` when no test
    provider is bound. Prefer injecting :class:`PythonVersionProvider` over
    calling this class directly.

    Example:
        >>> from pyiv.version import SysPythonVersionProvider
        >>> from pyiv.pep440 import Pep440VersionParser
        >>> ver = SysPythonVersionProvider().get_version()
        >>> Pep440VersionParser().is_version_compatible(ver, ">=3.8")
        True
    """

    def get_version(self) -> str:
        """Return ``major.minor.micro`` for :data:`sys.version_info`."""
        info = sys.version_info
        return f"{info.major}.{info.minor}.{info.micro}"


class FixedPythonVersionProvider(PythonVersionProvider):
    """Test double that returns a fixed interpreter version string.

    **Why this exists:** Exercise version-conditioned bindings under many
    Python versions without changing the real runtime. Bind with
    ``binder.bind(PythonVersionProvider).to_instance(...)``.

    Example:
        >>> from pyiv.version import FixedPythonVersionProvider
        >>> FixedPythonVersionProvider("3.8.18").get_version()
        '3.8.18'
    """

    def __init__(self, version: str) -> None:
        """
        Args:
            version: PEP 440 version string to report (e.g. ``3.10.12``).
        """
        self._version = version

    def get_version(self) -> str:
        """Return the fixed version passed to the constructor."""
        return self._version


class PythonVersionSource:
    """:class:`VersionSource` that delegates to a :class:`PythonVersionProvider`.

    **Why this exists:** ``for_python_version`` registers this as the
    ``python`` domain source. At selection time it resolves (in order): an
    explicit constructor provider, a ``PythonVersionProvider`` bound on the
    config, then :class:`SysPythonVersionProvider`.

    Example:
        >>> from pyiv.version import FixedPythonVersionProvider, PythonVersionSource
        >>> PythonVersionSource(FixedPythonVersionProvider("3.9.0")).get_version()
        '3.9.0'
    """

    def __init__(
        self,
        provider: Optional[PythonVersionProvider] = None,
        *,
        config: Optional["Config"] = None,
    ) -> None:
        """
        Args:
            provider: Explicit provider (wins over config bindings).
            config: Config used to look up a bound ``PythonVersionProvider``.
        """
        self._provider = provider
        self._config = config

    def attach_config(self, config: "Config") -> None:
        """Point this source at the (possibly merged) config used for selection.

        ``install`` / ``override`` may replace a submodule's
        ``PythonVersionSource`` whose ``config=`` still references that
        submodule. Selection rebinds sources to the final merged config.
        """
        self._config = config

    def get_version(self) -> Optional[str]:
        """Return the resolved provider's version string."""
        return self._resolve_provider().get_version()

    def _resolve_provider(self) -> PythonVersionProvider:
        if self._provider is not None:
            return self._provider
        if self._config is not None:
            inst = self._config.get_instance(PythonVersionProvider)
            if inst is not None:
                return inst  # type: ignore[no-any-return]
            reg = self._config.get_registration(PythonVersionProvider)
            if isinstance(reg, type) and issubclass(reg, PythonVersionProvider):
                return reg()
        return SysPythonVersionProvider()


class MapVersionSource:
    """Fixed version map for tests and host-supplied environment snapshots.

    **Why this exists:** Selection must be deterministic in unit tests without
    monkeypatching ``sys`` or ``importlib.metadata``. Use it for
    ``for_package_version`` ranges and to simulate an installed distribution
    for ``for_package_present`` (register under
    :func:`package_version_domain`). Bind one domain key, or pass a multi-key
    map and select with ``domain``.

    Example:
        >>> from pyiv.version import MapVersionSource, package_version_domain
        >>> MapVersionSource({"requests": "2.31.0"}, domain="requests").get_version()
        '2.31.0'
        >>> MapVersionSource({"alpine": "3.19"}).get_version()
        '3.19'
        >>> domain = package_version_domain("cjson")
        >>> MapVersionSource({domain: "1.0.0"}).get_version()
        '1.0.0'
    """

    def __init__(
        self,
        versions: Mapping[str, str],
        *,
        domain: Optional[str] = None,
    ) -> None:
        """
        Args:
            versions: Mapping of domain name → version string.
            domain: Domain to read. When omitted and ``versions`` has exactly
                one entry, that entry is used.
        """
        self._versions: Dict[str, str] = dict(versions)
        if domain is not None:
            self._domain = domain
        elif len(self._versions) == 1:
            self._domain = next(iter(self._versions))
        else:
            raise ValueError("MapVersionSource requires domain= when versions has " "multiple keys")

    def get_version(self) -> Optional[str]:
        """Return the configured version for this source's domain, if any."""
        return self._versions.get(self._domain)


@dataclass(frozen=True)
class VersionBindingCandidate:
    """One version-conditioned alternative for an abstract type.

    **Why this exists:** Unconditional ``Config`` registrations are last-wins
    dictionaries. Version alternatives (including package presence /
    absence) must accumulate as candidates and be selected after config
    composition. Hosts rarely construct this type directly — prefer
    ``binder.bind(...).to(...).for_version(...)`` /
    ``for_package_present`` / ``for_package_absent``.

    Example:
        >>> from pyiv.version import PACKAGE_PRESENT, VersionBindingCandidate
        >>> class HttpClient:
        ...     pass
        >>> class LegacyClient(HttpClient):
        ...     pass
        >>> c = VersionBindingCandidate(
        ...     abstract=HttpClient,
        ...     domain="package:requests",
        ...     specifier="<2.30",
        ...     implementation=LegacyClient,
        ... )
        >>> c.specifier
        '<2.30'
        >>> VersionBindingCandidate(
        ...     abstract=HttpClient,
        ...     domain="package:cjson",
        ...     specifier=PACKAGE_PRESENT,
        ...     implementation=LegacyClient,
        ... ).specifier
        '*'
    """

    abstract: Type[Any]
    domain: str
    specifier: str
    implementation: Optional[Type[Any]] = None
    instance: Any = None
    provider: Optional[Provider[Any]] = None
    scope: Optional[Scope] = None
    parser_name: Optional[str] = None


def __getattr__(name: str) -> Any:
    """Lazy re-export of :class:`~pyiv.pep440.Pep440VersionParser`.

    Keeps :mod:`pyiv.pep440` free to subclass :class:`InvalidVersion` without
    a circular import at module load.
    """
    if name == "Pep440VersionParser":
        from pyiv.pep440 import Pep440VersionParser

        return Pep440VersionParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
