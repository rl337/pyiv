"""Strict behavior when version-conditioned bindings mix with other registrations.

These tests are the contract for the guide section
"Mixing with other bindings" in docs/guide/version-bindings.rst.
"""

from __future__ import annotations

import pytest

from pyiv import Config, CreationError, get_injector, override
from pyiv.provider import Provider
from pyiv.scope import SingletonScope
from pyiv.version import FixedPythonVersionProvider, PythonVersionProvider


class Service:
    kind = "base"


class Legacy(Service):
    kind = "legacy"


class Modern(Service):
    kind = "modern"


class Fallback(Service):
    kind = "fallback"


class Other:
    kind = "other"


def _python(binder, version: str) -> None:
    binder.bind(PythonVersionProvider).to_instance(FixedPythonVersionProvider(version))


# --- Unconditional fallback -------------------------------------------------


def test_match_wins_over_unconditional_fallback_registered_after() -> None:
    """A matching version candidate is preferred over a later unconditional bind."""

    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.12.0")
            b.bind(Service).to(Legacy).for_python_version("<3.11")
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            b.bind(Service).to(Fallback)

    assert get_injector(C).inject(Service).kind == "modern"


def test_unconditional_fallback_used_when_no_version_match() -> None:
    """Zero matching candidates → keep the unconditional binding as fallback."""

    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.9.0")
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            b.bind(Service).to(Fallback)

    assert get_injector(C).inject(Service).kind == "fallback"


def test_unconditional_before_version_to_is_lost() -> None:
    """Ordering footgun: bind().to() before for_version overwrites then retracts.

    An unconditional ``bind(Service).to(Fallback)`` followed by
    ``bind(Service).to(Modern).for_python_version(...)`` loses Fallback because
    ``.to(Modern)`` last-wins into registrations before ``for_version`` retracts
    that registration into the candidate list. Documented: register fallbacks
    **after** all version-conditioned binds for that type.
    """

    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.9.0")
            b.bind(Service).to(Fallback)
            b.bind(Service).to(Modern).for_python_version(">=3.11")

    with pytest.raises(CreationError, match="No version-compatible"):
        get_injector(C)


def test_ambiguous_version_match_ignores_unconditional_fallback() -> None:
    """Overlapping version candidates error even if a fallback exists."""

    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.11.0")
            b.bind(Service).to(Legacy).for_python_version(">=3.10")
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            b.bind(Service).to(Fallback)

    with pytest.raises(CreationError, match="Ambiguous") as exc_info:
        get_injector(C)
    assert exc_info.value.ambiguous is True


# --- register() API alongside Binder ----------------------------------------


def test_register_unconditional_after_version_candidates_is_fallback() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.9.0")
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            self.register(Service, Fallback)

    assert get_injector(C).inject(Service).kind == "fallback"


def test_register_then_version_to_overwrites_like_binder() -> None:
    class C(Config):
        def configure(self):
            self.register(Service, Fallback)
            b = self.get_binder()
            _python(b, "3.9.0")
            b.bind(Service).to(Modern).for_python_version(">=3.11")

    with pytest.raises(CreationError, match="No version-compatible"):
        get_injector(C)


# --- Providers and instances ------------------------------------------------


def test_version_candidate_to_provider() -> None:
    class ModernProvider(Provider[Service]):
        def get(self) -> Service:
            return Modern()

    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.12.0")
            b.bind(Service).to_provider(ModernProvider()).for_python_version(">=3.11")
            b.bind(Service).to(Fallback)

    assert get_injector(C).inject(Service).kind == "modern"


def test_version_candidate_to_instance() -> None:
    modern = Modern()

    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.12.0")
            b.bind(Service).to_instance(modern).for_python_version(">=3.11")
            b.bind(Service).to(Fallback)

    assert get_injector(C).inject(Service) is modern


def test_unconditional_provider_fallback_when_no_match() -> None:
    class FallbackProvider(Provider[Service]):
        def get(self) -> Service:
            return Fallback()

    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.9.0")
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            b.bind(Service).to_provider(FallbackProvider())

    assert get_injector(C).inject(Service).kind == "fallback"


# --- Scopes -----------------------------------------------------------------


def test_winning_version_candidate_keeps_scope() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.12.0")
            b.bind(Service).to(Modern).for_python_version(">=3.11").in_scope(SingletonScope())
            b.bind(Service).to(Fallback)

    inj = get_injector(C)
    assert inj.inject(Service) is inj.inject(Service)
    assert inj.inject(Service).kind == "modern"


def test_fallback_can_be_scoped_when_no_match() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.9.0")
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            b.bind(Service).to(Fallback).in_scope(SingletonScope())

    inj = get_injector(C)
    assert inj.inject(Service) is inj.inject(Service)
    assert inj.inject(Service).kind == "fallback"


# --- install / override -----------------------------------------------------


def test_install_accumulates_version_candidates_from_library() -> None:
    class Lib(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.10.0")
            b.bind(Service).to(Legacy).for_python_version("<3.11")
            b.bind(Service).to(Modern).for_python_version(">=3.11")

    class Host(Config):
        def configure(self):
            self.install(Lib)
            # Host-only unconditional fallback after install.
            self.get_binder().bind(Service).to(Fallback)

    assert get_injector(Host).inject(Service).kind == "legacy"


def test_install_host_adds_more_version_candidates() -> None:
    class Lib(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.12.0")
            b.bind(Service).to(Legacy).for_python_version("<3.11")

    class Host(Config):
        def configure(self):
            self.install(Lib)
            self.get_binder().bind(Service).to(Modern).for_python_version(">=3.11")

    assert get_injector(Host).inject(Service).kind == "modern"


def test_override_replaces_unconditional_but_keeps_version_candidates() -> None:
    """override merges version candidates (extend) and last-wins unconditional."""

    class Base(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.9.0")
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            b.bind(Service).to(Legacy)  # would be fallback on base alone

    class Test(Config):
        def configure(self):
            self.get_binder().bind(Service).to(Fallback)

    # No version match → Test's unconditional Fallback wins via merge replace.
    assert get_injector(override(Base).with_(Test)).inject(Service).kind == "fallback"


def test_override_can_add_matching_version_candidate() -> None:
    class Base(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.12.0")
            b.bind(Service).to(Legacy).for_python_version("<3.11")
            b.bind(Service).to(Fallback)

    class Test(Config):
        def configure(self):
            self.get_binder().bind(Service).to(Modern).for_python_version(">=3.11")

    assert get_injector(override(Base).with_(Test)).inject(Service).kind == "modern"


# --- Coexistence with unrelated bindings ------------------------------------


def test_version_selection_does_not_affect_other_types() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.12.0")
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            b.bind(Other).to(Other)

    inj = get_injector(C)
    assert inj.inject(Service).kind == "modern"
    assert isinstance(inj.inject(Other), Other)


def test_unrelated_unconditional_survives_version_retract_on_other_type() -> None:
    class C(Config):
        def configure(self):
            b = self.get_binder()
            _python(b, "3.9.0")
            b.bind(Other).to(Other)
            b.bind(Service).to(Modern).for_python_version(">=3.11")
            b.bind(Service).to(Fallback)

    inj = get_injector(C)
    assert inj.inject(Service).kind == "fallback"
    assert isinstance(inj.inject(Other), Other)
