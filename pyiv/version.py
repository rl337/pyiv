"""Version sources, comparers, and version-conditioned bindings.

Select among multiple implementations of the same interface based on a
**named version domain** — installed package versions, the running Python
interpreter, or any host-defined domain (OS release, wire protocol, …).

**What Problem Does This Solve?**

Hosts inherit transitive dependency versions they do not pin directly. Adapter
libraries need to register several implementations and let the injector pick
the one compatible with the environment. The same mechanism covers interpreter
specialization (``async`` APIs that differ by Python version) and non-Python
domains when the host supplies a :class:`VersionSource` and optional custom
:class:`VersionComparer`.

**Real-World Use Cases:**

- Pick an HTTP adapter compatible with the installed ``requests`` distribution
- Use ``TaskGroup``-based runners only on Python 3.11+
- Bind filesystem helpers based on the host OS release (custom comparer)
- Tests bind a :class:`FixedPythonVersionProvider` (or a fixed
  :class:`MapVersionSource`) instead of monkeypatching ``sys`` /
  ``importlib.metadata``

Architecture:

- :class:`VersionSource` — obtains the current version string for a domain
- :class:`VersionComparer` — ``compatible`` / ``less`` / ``greater`` predicates
- :class:`Pep440VersionComparer` — default PEP 440 comparer for Python/package
- :class:`PythonVersionProvider` — injectable interpreter version (sys or fixed)
- Fluent Binder: ``.for_version`` / ``.for_package_version`` /
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

    Custom domain with a host comparer::

        >>> from pyiv import Config, get_injector
        >>> from pyiv.version import MapVersionSource, VersionComparer
        >>> class FsTool:
        ...     name = "base"
        >>> class AlpineFs(FsTool):
        ...     name = "alpine"
        >>> class DebFs(FsTool):
        ...     name = "deb"
        >>> class AlpineComparer:
        ...     '''Treat dotted release numbers as integer tuples.'''
        ...     def is_version_compatible(self, version, specifier):
        ...         # Simple demo: specifier is '>=X.Y' only
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
        ...         binder.version_source("alpine", MapVersionSource({"alpine": "3.19.0"}))
        ...         binder.version_comparer("alpine", AlpineComparer())
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

from pyiv import _pep440
from pyiv.provider import Provider
from pyiv.scope import Scope

if TYPE_CHECKING:
    from pyiv.config import Config

# Built-in domain names for convenience adapters.
PYTHON_VERSION_DOMAIN = "python"


def package_version_domain(distribution: str) -> str:
    """Return the version-domain key for an installed distribution name."""
    return f"package:{distribution}"


__all__ = [
    "VersionComparer",
    "VersionSource",
    "Pep440VersionComparer",
    "PackageVersionSource",
    "PythonVersionProvider",
    "SysPythonVersionProvider",
    "FixedPythonVersionProvider",
    "PythonVersionSource",
    "MapVersionSource",
    "VersionBindingCandidate",
    "PYTHON_VERSION_DOMAIN",
    "package_version_domain",
]


@runtime_checkable
class VersionComparer(Protocol):
    """Compares and matches version strings for a domain.

    **Why this exists:** Python package and interpreter versions follow
    :pep:`440`, but hosts often condition bindings on OS releases, wire
    protocols, or schema epochs that do not. Depend on this protocol when you
    need a custom ordering or specifier grammar; register it with
    :meth:`pyiv.binder.Binder.version_comparer`.

    Example:
        >>> from pyiv.version import Pep440VersionComparer
        >>> c = Pep440VersionComparer()
        >>> c.is_version_compatible("2.31.0", ">=2.30,<3")
        True
        >>> c.is_version_less("1.0", "2.0")
        True
        >>> c.is_version_greater("2.0", "1.0")
        True
    """

    def is_version_compatible(self, version: str, specifier: str) -> bool:
        """Return True if ``version`` satisfies ``specifier`` for this domain."""
        ...

    def is_version_less(self, a: str, b: str) -> bool:
        """Return True if ``a`` is strictly less than ``b``."""
        ...

    def is_version_greater(self, a: str, b: str) -> bool:
        """Return True if ``a`` is strictly greater than ``b``."""
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


class Pep440VersionComparer:
    """Default :class:`VersionComparer` using :pep:`440` rules.

    **Why this exists:** Package and interpreter convenience APIs
    (``for_package_version``, ``for_python_version``) need a standards-based
    matcher without adding a third-party runtime dependency. Custom domains
    may reuse this when their versions are already PEP 440 strings.

    Example:
        >>> from pyiv.version import Pep440VersionComparer
        >>> c = Pep440VersionComparer()
        >>> c.is_version_compatible("3.11.5", ">=3.11,<3.12")
        True
        >>> c.is_version_compatible("3.10.9", ">=3.11")
        False
        >>> c.is_version_less("3.10", "3.11")
        True
    """

    def is_version_compatible(self, version: str, specifier: str) -> bool:
        """Return whether ``version`` satisfies the PEP 440 ``specifier``."""
        try:
            return _pep440.SpecifierSet(specifier).contains(version)
        except (_pep440.InvalidVersion, _pep440.InvalidSpecifier) as exc:
            raise ValueError(str(exc)) from exc

    def is_version_less(self, a: str, b: str) -> bool:
        """Return whether PEP 440 version ``a`` is strictly less than ``b``."""
        try:
            return _pep440.Version(a) < _pep440.Version(b)
        except _pep440.InvalidVersion as exc:
            raise ValueError(str(exc)) from exc

    def is_version_greater(self, a: str, b: str) -> bool:
        """Return whether PEP 440 version ``a`` is strictly greater than ``b``."""
        try:
            return _pep440.Version(a) > _pep440.Version(b)
        except _pep440.InvalidVersion as exc:
            raise ValueError(str(exc)) from exc


class PackageVersionSource:
    """Read an installed distribution version via ``importlib.metadata``.

    **Why this exists:** ``for_package_version`` needs the **distribution**
    name (as on PyPI), which is not always the import package name. This
    source never imports the library — it only consults packaging metadata.

    Example:
        >>> from pyiv.version import PackageVersionSource
        >>> # ``pyiv`` itself is installed in the test / docs environment
        >>> ver = PackageVersionSource("pyiv").get_version()
        >>> ver is None or len(ver.split(".")) >= 2
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
        >>> from pyiv.version import SysPythonVersionProvider, Pep440VersionComparer
        >>> ver = SysPythonVersionProvider().get_version()
        >>> Pep440VersionComparer().is_version_compatible(ver, ">=3.8")
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
    monkeypatching ``sys`` or ``importlib.metadata``. Bind one domain key, or
    pass a multi-key map and select with ``domain``.

    Example:
        >>> from pyiv.version import MapVersionSource
        >>> MapVersionSource({"requests": "2.31.0"}, domain="requests").get_version()
        '2.31.0'
        >>> MapVersionSource({"alpine": "3.19"}).get_version()
        '3.19'
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
    dictionaries. Version alternatives must accumulate as candidates and be
    selected after config composition. Hosts rarely construct this type
    directly — prefer ``binder.bind(...).to(...).for_version(...)``.

    Example:
        >>> from pyiv.version import VersionBindingCandidate
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
    """

    abstract: Type[Any]
    domain: str
    specifier: str
    implementation: Optional[Type[Any]] = None
    instance: Any = None
    provider: Optional[Provider[Any]] = None
    scope: Optional[Scope] = None
    comparer: Optional[VersionComparer] = None
