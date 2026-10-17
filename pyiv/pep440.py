"""Public :pep:`440` version parsing and specifier matching.

This module is the stdlib-only PEP 440 engine used by
:class:`Pep440VersionParser` (registered under the name ``\"PEP440\"`` on
:class:`~pyiv.config.Config`). Semantics follow :pep:`440` (release ordering,
prereleases, ``~=``, comma-combined specifiers). Prereleases are excluded from
matching unless the specifier itself names a prerelease (same default as
``packaging``).

**Why this exists:** Package and interpreter version domains need a real
PEP 440 matcher without a third-party runtime dependency. Hosts and tests can
import :class:`Version` / :class:`SpecifierSet` directly, or use the
:class:`~pyiv.version.VersionParser` façade :class:`Pep440VersionParser`.

Example:
    >>> from pyiv.pep440 import SpecifierSet, Version
    >>> Version("1.0") < Version("1.1")
    True
    >>> SpecifierSet(">=2.30,<3").contains("2.31.0")
    True
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple, Union

from pyiv.version import InvalidSpecifier as _InvalidSpecifierBase
from pyiv.version import InvalidVersion as _InvalidVersionBase

# PEP 440 public version pattern (simplified but covers released + pre/post/dev).
_VERSION_RE = re.compile(
    r"""
    ^\s*
    v?
    (?:(?P<epoch>[0-9]+)!)?
    (?P<release>[0-9]+(?:\.[0-9]+)*)
    (?P<pre>
        [-_\.]?
        (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
        [-_\.]?
        (?P<pre_n>[0-9]+)?
    )?
    (?P<post>
        (?:-(?P<post_n1>[0-9]+))
        |
        (?:[-_\.]?(?P<post_l>post|rev|r)[-_\.]?(?P<post_n2>[0-9]+)?)
    )?
    (?P<dev>
        [-_\.]?
        (?P<dev_l>dev)
        [-_\.]?
        (?P<dev_n>[0-9]+)?
    )?
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

_PRE_NORMALIZE = {
    "a": "a",
    "alpha": "a",
    "b": "b",
    "beta": "b",
    "c": "rc",
    "pre": "rc",
    "preview": "rc",
    "rc": "rc",
}


class InvalidVersion(_InvalidVersionBase):
    """Raised when a string is not a valid PEP 440 version.

    **Why this exists:** Subclasses :class:`pyiv.version.InvalidVersion` so
    callers can catch all parser failures, or only PEP 440 ones.

    Example:
        >>> from pyiv.pep440 import InvalidVersion
        >>> from pyiv.version import InvalidVersion as BaseInvalidVersion
        >>> issubclass(InvalidVersion, BaseInvalidVersion)
        True
    """


class InvalidSpecifier(_InvalidSpecifierBase):
    """Raised when a string is not a valid PEP 440 version specifier.

    **Why this exists:** Subclasses :class:`pyiv.version.InvalidSpecifier` (and
    therefore :class:`pyiv.version.InvalidVersion`) for PEP 440 constraints.

    Example:
        >>> from pyiv.pep440 import InvalidSpecifier
        >>> from pyiv.version import InvalidVersion
        >>> issubclass(InvalidSpecifier, InvalidVersion)
        True
    """


def _parse_letter_version(
    letter: Optional[str], number: Optional[str]
) -> Optional[Tuple[str, int]]:
    if letter is None and number is None:
        return None
    if letter is None:
        letter = "post"
    letter = _PRE_NORMALIZE.get(letter.lower(), letter.lower())
    return letter, int(number) if number else 0


class Version:
    """Comparable PEP 440 version."""

    def __init__(self, version: str) -> None:
        match = _VERSION_RE.search(version)
        if not match:
            raise InvalidVersion(f"Invalid PEP 440 version: {version!r}")
        self._raw = version.strip()
        epoch = match.group("epoch")
        self.epoch = int(epoch) if epoch else 0
        self.release = tuple(int(i) for i in match.group("release").split("."))
        self.pre = _parse_letter_version(match.group("pre_l"), match.group("pre_n"))
        post = match.group("post")
        if post is not None:
            if match.group("post_n1"):
                self.post: Optional[Tuple[str, int]] = ("post", int(match.group("post_n1")))
            else:
                self.post = _parse_letter_version(match.group("post_l"), match.group("post_n2"))
        else:
            self.post = None
        self.dev = _parse_letter_version(match.group("dev_l"), match.group("dev_n"))
        local = match.group("local")
        self.local: Optional[Tuple[Union[int, str], ...]] = (
            tuple(_parse_local_part(p) for p in re.split(r"[-_\.]", local)) if local else None
        )

    @property
    def is_prerelease(self) -> bool:
        return self.pre is not None or self.dev is not None

    def __str__(self) -> str:
        return self._raw

    def __repr__(self) -> str:
        return f"Version({self._raw!r})"

    def __hash__(self) -> int:
        return hash(self._key)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key == other._key

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key < other._key

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key <= other._key

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key > other._key

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key >= other._key

    @property
    def _key(self) -> Tuple:
        # Sort key aligned with PEP 440 / packaging.
        release = self.release
        while release and release[-1] == 0:
            release = release[:-1]

        if self.pre is not None:
            pre: Tuple = self.pre
        elif self.post is None and self.dev is not None:
            pre = ("", -1)  # dev without pre sorts before releases
        else:
            pre = ("z",)

        if self.post is not None:
            post: Tuple = self.post
        else:
            post = ("",)

        if self.dev is not None:
            dev: Tuple = self.dev
        else:
            dev = ("z",)

        if self.local is not None:
            local: Tuple = self.local
        else:
            local = (("*",),)

        return (self.epoch, release, pre, post, dev, local)


def _parse_local_part(part: str) -> Union[int, str]:
    if part.isdigit():
        return int(part)
    return part.lower()


_OPS = ("===", "==", "!=", "~=", "<=", ">=", "<", ">")


class Specifier:
    """Single PEP 440 version clause (e.g. ``>=2.30``)."""

    def __init__(self, spec: str) -> None:
        spec = spec.strip()
        op = None
        for candidate in _OPS:
            if spec.startswith(candidate):
                op = candidate
                rest = spec[len(candidate) :].strip()
                break
        if op is None or not rest:
            raise InvalidSpecifier(f"Invalid PEP 440 specifier: {spec!r}")
        self.operator = op
        self.version = rest
        # Validate version side (=== allows arbitrary strings; == / != allow .*).
        if op == "===":
            pass
        elif op in ("==", "!=") and rest.endswith(".*"):
            prefix = rest[:-2]
            if not prefix:
                raise InvalidSpecifier(f"Invalid PEP 440 specifier: {spec!r}")
            try:
                Version(prefix)
            except InvalidVersion as exc:
                raise InvalidSpecifier(f"Invalid PEP 440 specifier: {spec!r}") from exc
        else:
            try:
                Version(rest)
            except InvalidVersion as exc:
                raise InvalidSpecifier(f"Invalid PEP 440 specifier: {spec!r}") from exc

    def contains(self, version: Union[str, Version], prereleases: Optional[bool] = None) -> bool:
        item = version if isinstance(version, Version) else Version(version)
        if prereleases is None:
            prereleases = self._accepts_prereleases()
        if not prereleases and item.is_prerelease:
            return False
        return self._compare(item)

    def _accepts_prereleases(self) -> bool:
        try:
            return Version(self.version).is_prerelease
        except InvalidVersion:
            return False

    def _compare(self, item: Version) -> bool:
        op = self.operator
        if op == "===":
            return str(item) == self.version
        if op == "==":
            return self._equal(item)
        if op == "!=":
            return not self._equal(item)
        spec_v = Version(self.version)
        if op == ">":
            return item > spec_v
        if op == ">=":
            return item >= spec_v
        if op == "<":
            return item < spec_v and not self._prefix_reject_lt(item, spec_v)
        if op == "<=":
            return item <= spec_v
        if op == "~=":
            return self._compatible(item, spec_v)
        raise InvalidSpecifier(f"Unknown operator {op!r}")

    def _equal(self, item: Version) -> bool:
        if self.version.endswith(".*"):
            return self._prefix_match(item, self.version)
        return item == Version(self.version)

    def _prefix_match(self, item: Version, pattern: str) -> bool:
        if not pattern.endswith(".*"):
            raise InvalidSpecifier(f"Invalid equality pattern: {pattern!r}")
        prefix = pattern[:-2]
        # Compare release prefix ignoring local/pre when matching ==1.1.*
        try:
            prefix_v = Version(prefix)
        except InvalidVersion as exc:
            raise InvalidSpecifier(f"Invalid equality pattern: {pattern!r}") from exc
        item_rel = item.release
        prefix_rel = prefix_v.release
        if len(item_rel) < len(prefix_rel):
            item_rel = item_rel + (0,) * (len(prefix_rel) - len(item_rel))
        return item_rel[: len(prefix_rel)] == prefix_rel and item.epoch == prefix_v.epoch

    def _prefix_reject_lt(self, item: Version, spec_v: Version) -> bool:
        # Local versions are excluded from < comparisons per packaging rules.
        return item.local is not None and item.release == spec_v.release

    def _compatible(self, item: Version, spec_v: Version) -> bool:
        # ~=2.2 means >=2.2, ==2.*
        if item < spec_v:
            return False
        if len(spec_v.release) < 2:
            raise InvalidSpecifier(f"~= requires at least two release segments: {self.version!r}")
        prefix = ".".join(str(p) for p in spec_v.release[:-1]) + ".*"
        return Specifier(f"=={prefix}").contains(item, prereleases=True)


class SpecifierSet:
    """Comma-combined PEP 440 specifiers (AND)."""

    def __init__(self, specifiers: str = "") -> None:
        self._specs: List[Specifier] = []
        for part in specifiers.split(","):
            part = part.strip()
            if not part:
                continue
            self._specs.append(Specifier(part))

    def __str__(self) -> str:
        return ",".join(f"{s.operator}{s.version}" for s in self._specs)

    def __repr__(self) -> str:
        return f"SpecifierSet({str(self)!r})"

    def __bool__(self) -> bool:
        return bool(self._specs)

    def contains(
        self,
        version: Union[str, Version],
        prereleases: Optional[bool] = None,
    ) -> bool:
        if not self._specs:
            return True
        item = version if isinstance(version, Version) else Version(version)
        if prereleases is None:
            prereleases = any(spec._accepts_prereleases() for spec in self._specs)
        if not prereleases and item.is_prerelease:
            return False
        return all(spec.contains(item, prereleases=True) for spec in self._specs)

    def filter(
        self, iterable: Iterable[Union[str, Version]], prereleases: Optional[bool] = None
    ) -> List[Version]:
        return [
            (v if isinstance(v, Version) else Version(v))
            for v in iterable
            if self.contains(v, prereleases=prereleases)
        ]


class Pep440VersionParser:
    """:class:`~pyiv.version.VersionParser` implementation for :pep:`440`.

    **Why this exists:** Python package and interpreter domains need a named,
    standards-based parser. Config registers this under
    :data:`pyiv.version.PEP440` by default so
    ``for_package_version`` / ``for_python_version`` work without extra setup.

    Example:
        >>> from pyiv.pep440 import Pep440VersionParser
        >>> p = Pep440VersionParser()
        >>> p.is_version_compatible("3.11.5", ">=3.11,<3.12")
        True
        >>> p.is_version_less("3.10", "3.11")
        True
        >>> p.is_version_greater("2.0", "1.0")
        True
    """

    def is_version_compatible(self, version: str, specifier: str) -> bool:
        """Return whether ``version`` satisfies the PEP 440 ``specifier``.

        Raises:
            InvalidVersion: If ``version`` or ``specifier`` is not PEP 440.
        """
        return SpecifierSet(specifier).contains(version)

    def is_version_less(self, a: str, b: str) -> bool:
        """Return whether PEP 440 version ``a`` is strictly less than ``b``.

        Raises:
            InvalidVersion: If either string is not a PEP 440 version.
        """
        return Version(a) < Version(b)

    def is_version_greater(self, a: str, b: str) -> bool:
        """Return whether PEP 440 version ``a`` is strictly greater than ``b``.

        Raises:
            InvalidVersion: If either string is not a PEP 440 version.
        """
        return Version(a) > Version(b)
