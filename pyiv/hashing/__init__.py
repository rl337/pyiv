"""Injectable digests and HMAC."""

from __future__ import annotations

import hashlib
import hmac
from abc import ABC, abstractmethod
from typing import Optional, Union


class Hasher(ABC):
    """Injectable digest / HMAC helper.

    **Why this exists:** Call sites that hard-code ``hashlib`` are harder to
    stub for fixed digests in tests.

    Example:
        >>> from pyiv.hashing import RealHasher
        >>> h: Hasher = RealHasher()
        >>> h.digest("sha256", b"abc").hex()[:8]
        'ba7816bf'
    """

    @abstractmethod
    def digest(self, algorithm: str, data: bytes) -> bytes:
        """Return a digest of ``data`` using ``algorithm``."""

    @abstractmethod
    def hmac_digest(self, algorithm: str, key: bytes, data: bytes) -> bytes:
        """Return HMAC of ``data`` with ``key``."""


class RealHasher(Hasher):
    """Hasher backed by ``hashlib`` / ``hmac``.

    **Why this exists:** Production digests via the standard library.
    """

    def digest(self, algorithm: str, data: bytes) -> bytes:
        return hashlib.new(algorithm, data).digest()

    def hmac_digest(self, algorithm: str, key: bytes, data: bytes) -> bytes:
        return hmac.new(key, data, algorithm).digest()


class SyntheticHasher(Hasher):
    """Hasher that returns fixed digests (optional) for tests.

    **Why this exists:** Assert hashing call shapes without real crypto cost.

    Example:
        >>> h = SyntheticHasher(fixed=b"\\x00\\x01")
        >>> h.digest("sha256", b"x")
        b'\\x00\\x01'
    """

    def __init__(self, fixed: Optional[bytes] = None) -> None:
        self._fixed = fixed
        self.calls = []

    def digest(self, algorithm: str, data: bytes) -> bytes:
        self.calls.append(("digest", algorithm, data))
        if self._fixed is not None:
            return self._fixed
        return hashlib.new(algorithm, data).digest()

    def hmac_digest(self, algorithm: str, key: bytes, data: bytes) -> bytes:
        self.calls.append(("hmac", algorithm, key, data))
        if self._fixed is not None:
            return self._fixed
        return hmac.new(key, data, algorithm).digest()


__all__ = ["Hasher", "RealHasher", "SyntheticHasher"]
