"""Tests for version-conditioned DI bindings."""

from __future__ import annotations

import pytest

from pyiv import Config, CreationError, get_injector
from pyiv.pep440 import Pep440VersionParser
from pyiv.scope import SingletonScope
from pyiv.version import (
    FixedPythonVersionProvider,
    InvalidVersion,
    MapVersionSource,
    PackageVersionSource,
    PythonVersionProvider,
    PythonVersionSource,
    SysPythonVersionProvider,
    package_version_domain,
)


class Runner:
    kind = "base"


class LegacyRunner(Runner):
    kind = "legacy"


class ModernRunner(Runner):
    kind = "modern"


class FallbackRunner(Runner):
    kind = "fallback"


def _bind_python(binder, version: str) -> None:
    binder.bind(PythonVersionProvider).to_instance(FixedPythonVersionProvider(version))


@pytest.mark.parametrize(
    "version,expected",
    [
        ("3.8.18", "legacy"),
        ("3.10.12", "legacy"),
        ("3.11.0", "modern"),
        ("3.12.1", "modern"),
    ],
)
def test_python_version_provider_matrix(version: str, expected: str) -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _bind_python(b, version)
            b.bind(Runner).to(LegacyRunner).for_python_version("<3.11")
            b.bind(Runner).to(ModernRunner).for_python_version(">=3.11")

    inj = get_injector(C)
    assert inj.inject(Runner).kind == expected
    assert inj.inject(PythonVersionProvider).get_version() == version


def test_unconditional_fallback_when_no_match() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _bind_python(b, "3.9.0")
            b.bind(Runner).to(ModernRunner).for_python_version(">=3.11")
            b.bind(Runner).to(FallbackRunner)

    assert get_injector(C).inject(Runner).kind == "fallback"


def test_no_match_without_fallback_errors() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _bind_python(b, "3.9.0")
            b.bind(Runner).to(ModernRunner).for_python_version(">=3.11")

    with pytest.raises(CreationError, match="No version-compatible"):
        get_injector(C)


def test_overlapping_matches_are_ambiguous() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _bind_python(b, "3.11.0")
            b.bind(Runner).to(LegacyRunner).for_python_version(">=3.10")
            b.bind(Runner).to(ModernRunner).for_python_version(">=3.11")

    with pytest.raises(CreationError, match="Ambiguous") as exc_info:
        get_injector(C)
    assert exc_info.value.ambiguous is True


def test_package_version_with_map_source() -> None:
    class HttpClient:
        name = "base"

    class Legacy(HttpClient):
        name = "legacy"

    class Modern(HttpClient):
        name = "modern"

    domain = package_version_domain("requests")

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.version_source(domain, MapVersionSource({domain: "2.31.0"}))
            b.bind(HttpClient).to(Legacy).for_package_version("requests", "<2.30")
            b.bind(HttpClient).to(Modern).for_package_version("requests", ">=2.30,<3")

    assert get_injector(C).inject(HttpClient).name == "modern"


def test_absent_package_without_fallback_errors() -> None:
    class HttpClient:
        pass

    class Legacy(HttpClient):
        pass

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(HttpClient).to(Legacy).for_package_version(
                "pyiv-definitely-not-installed-xyz", ">=1"
            )

    with pytest.raises(CreationError, match="absent|unknown|No version-compatible"):
        get_injector(C)


def test_for_package_present_selects_when_installed() -> None:
    class Encoder:
        kind = "base"

    class Fast(Encoder):
        kind = "fast"

    class Std(Encoder):
        kind = "std"

    domain = package_version_domain("cjson")

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.version_source(domain, MapVersionSource({domain: "2.1.0"}))
            b.bind(Encoder).to(Fast).for_package_present("cjson")
            b.bind(Encoder).to(Std)

    assert get_injector(C).inject(Encoder).kind == "fast"


def test_for_package_present_fallback_when_absent() -> None:
    class Encoder:
        kind = "base"

    class Fast(Encoder):
        kind = "fast"

    class Std(Encoder):
        kind = "std"

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(Encoder).to(Fast).for_package_present("pyiv-definitely-not-installed-xyz")
            b.bind(Encoder).to(Std)

    assert get_injector(C).inject(Encoder).kind == "std"


def test_for_package_present_without_fallback_errors() -> None:
    class Encoder:
        pass

    class Fast(Encoder):
        pass

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(Encoder).to(Fast).for_package_present("pyiv-definitely-not-installed-xyz")

    with pytest.raises(CreationError, match="absent|unknown|No version-compatible"):
        get_injector(C)


def test_for_package_version_star_is_presence() -> None:
    """``for_package_version(dist, \"*\")`` matches the same as for_package_present."""
    from pyiv.version import PACKAGE_PRESENT

    class Encoder:
        kind = "base"

    class Fast(Encoder):
        kind = "fast"

    domain = package_version_domain("accel")

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.version_source(domain, MapVersionSource({domain: "0.1"}))
            b.bind(Encoder).to(Fast).for_package_version("accel", PACKAGE_PRESENT)

    assert get_injector(C).inject(Encoder).kind == "fast"


def test_for_package_absent_selects_when_missing() -> None:
    class Encoder:
        kind = "base"

    class Fast(Encoder):
        kind = "fast"

    class Std(Encoder):
        kind = "std"

    missing = "pyiv-definitely-not-installed-xyz"

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(Encoder).to(Fast).for_package_present(missing)
            b.bind(Encoder).to(Std).for_package_absent(missing)

    assert get_injector(C).inject(Encoder).kind == "std"


def test_for_package_absent_skips_when_installed() -> None:
    class Encoder:
        kind = "base"

    class Fast(Encoder):
        kind = "fast"

    class Std(Encoder):
        kind = "std"

    domain = package_version_domain("cjson")

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.version_source(domain, MapVersionSource({domain: "1.0.0"}))
            b.bind(Encoder).to(Fast).for_package_present("cjson")
            b.bind(Encoder).to(Std).for_package_absent("cjson")

    assert get_injector(C).inject(Encoder).kind == "fast"


def test_for_package_absent_without_present_pair_when_installed_errors() -> None:
    """Only an absent candidate + installed package → zero matches → error."""
    class Encoder:
        pass

    class Std(Encoder):
        pass

    domain = package_version_domain("cjson")

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.version_source(domain, MapVersionSource({domain: "1.0.0"}))
            b.bind(Encoder).to(Std).for_package_absent("cjson")

    with pytest.raises(CreationError, match="No version-compatible|installed"):
        get_injector(C)


def test_for_package_version_bang_is_absence() -> None:
    from pyiv.version import PACKAGE_ABSENT

    class Encoder:
        kind = "base"

    class Std(Encoder):
        kind = "std"

    missing = "pyiv-definitely-not-installed-xyz"

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(Encoder).to(Std).for_package_version(missing, PACKAGE_ABSENT)

    assert get_injector(C).inject(Encoder).kind == "std"


def test_custom_named_version_parser() -> None:
    class FsTool:
        name = "base"

    class AlpineFs(FsTool):
        name = "alpine"

    class AlpineVersionParser:
        def is_version_compatible(self, version: str, specifier: str) -> bool:
            if not specifier.startswith(">="):
                raise InvalidVersion(f"unsupported specifier: {specifier!r}")
            return self._t(version) >= self._t(specifier[2:])

        def is_version_less(self, a: str, b: str) -> bool:
            return self._t(a) < self._t(b)

        def is_version_greater(self, a: str, b: str) -> bool:
            return self._t(a) > self._t(b)

        @staticmethod
        def _t(s: str):
            return tuple(int(p) for p in s.split("."))

    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.version_parser("alpine-release", AlpineVersionParser())
            b.version_source("alpine", MapVersionSource({"alpine": "3.19.0"}))
            b.use_version_parser("alpine", "alpine-release")
            b.bind(FsTool).to(AlpineFs).for_version("alpine", ">=3.18")

    assert get_injector(C).inject(FsTool).name == "alpine"


def test_scope_preserved_on_version_candidate() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _bind_python(b, "3.12.0")
            b.bind(Runner).to(ModernRunner).for_python_version(">=3.11").in_scope(SingletonScope())

    inj = get_injector(C)
    assert inj.inject(Runner) is inj.inject(Runner)


def test_install_merges_version_candidates() -> None:
    class Lib(Config):
        def configure(self):
            b = self.get_binder()
            _bind_python(b, "3.10.0")
            b.bind(Runner).to(LegacyRunner).for_python_version("<3.11")

    class Host(Config):
        def configure(self):
            self.install(Lib)
            b = self.get_binder()
            b.bind(Runner).to(ModernRunner).for_python_version(">=3.11")

    assert get_injector(Host).inject(Runner).kind == "legacy"


def test_default_sys_provider_is_injectable() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(Runner).to(ModernRunner).for_python_version(">=3.8")

    inj = get_injector(C)
    provider = inj.inject(PythonVersionProvider)
    assert isinstance(provider, SysPythonVersionProvider)
    assert Pep440VersionParser().is_version_compatible(provider.get_version(), ">=3.8")


def test_explicit_python_version_source_provider() -> None:
    src = PythonVersionSource(FixedPythonVersionProvider("3.9.1"))
    assert src.get_version() == "3.9.1"


def test_pep440_parser_helpers() -> None:
    p = Pep440VersionParser()
    assert p.is_version_compatible("1.2.3", ">=1.2,<2")
    assert p.is_version_less("1.0", "2.0")
    assert p.is_version_greater("2.0", "1.0")
    with pytest.raises(InvalidVersion):
        p.is_version_compatible("nope", ">=1")


def test_python_and_package_sources_smoke() -> None:
    assert SysPythonVersionProvider().get_version() is not None
    ver = PackageVersionSource("pyiv").get_version()
    assert ver is None or isinstance(ver, str)


def test_for_version_requires_target() -> None:
    class C(Config):
        def configure(self):
            with pytest.raises(ValueError, match="requires"):
                self.get_binder().bind(Runner).for_python_version(">=3.11")
