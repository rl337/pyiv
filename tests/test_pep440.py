"""Oracle tests for the public PEP 440 helper against packaging."""

from __future__ import annotations

import pytest
from packaging.specifiers import SpecifierSet as PkgSpecifierSet
from packaging.version import Version as PkgVersion

from pyiv.pep440 import InvalidSpecifier, InvalidVersion, SpecifierSet, Version
from pyiv.version import InvalidVersion as BaseInvalidVersion


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("1.0", "1.0.0", False),  # equal after trailing-zero normalization
        ("1.0.0", "1.0.1", True),
        ("1.0.1", "1.0.0", False),
        ("1.0a1", "1.0", True),
        ("1.0", "1.0.post1", True),
        ("2.0", "1.9.9", False),
        ("1.0.dev1", "1.0a1", True),
    ],
)
def test_version_ordering_matches_packaging(a: str, b: str, expected: bool) -> None:
    assert (Version(a) < Version(b)) is expected
    assert (PkgVersion(a) < PkgVersion(b)) is expected


@pytest.mark.parametrize(
    "version,specifier,expected",
    [
        ("2.30.0", ">=2.30,<3", True),
        ("2.29.9", ">=2.30,<3", False),
        ("3.0.0", ">=2.30,<3", False),
        ("2.30.0a1", ">=2.30", False),
        ("2.30.0a1", ">=2.30.0a1", True),
        ("1.4.5", "~=1.4.2", True),
        ("1.5.0", "~=1.4.2", False),
        ("3.11.0", ">=3.11", True),
        ("3.10.9", ">=3.11", False),
        ("1.1.2", "==1.1.*", True),
        ("1.2.0", "==1.1.*", False),
    ],
)
def test_specifier_contains_matches_packaging(version: str, specifier: str, expected: bool) -> None:
    assert SpecifierSet(specifier).contains(version) is expected
    assert PkgSpecifierSet(specifier).contains(version) is expected


def test_invalid_version_and_specifier() -> None:
    with pytest.raises(InvalidVersion):
        Version("not-a-version!!!")
    with pytest.raises(InvalidSpecifier):
        SpecifierSet(">>>>1.0")


def test_pep440_errors_subclass_version_interface() -> None:
    assert issubclass(InvalidVersion, BaseInvalidVersion)
    assert issubclass(InvalidSpecifier, BaseInvalidVersion)
