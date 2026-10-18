"""Injectable entropy / randomness for testable nonces."""

from __future__ import annotations

import random
import secrets
from abc import ABC, abstractmethod
from typing import Optional, Sequence, TypeVar

T = TypeVar("T")


class Entropy(ABC):
    """Injectable source of randomness.

    **Why this exists:** ``secrets`` / ``random`` at call sites make tests
    flaky. Inject ``Entropy`` and bind ``SyntheticEntropy`` with a seed.

    Example:
        >>> from pyiv.entropy import SyntheticEntropy
        >>> e: Entropy = SyntheticEntropy(seed=1)
        >>> len(e.randbytes(4))
        4
    """

    @abstractmethod
    def randbytes(self, n: int) -> bytes:
        """Return ``n`` random bytes."""

    @abstractmethod
    def token_urlsafe(self, nbytes: int = 32) -> str:
        """Return a URL-safe token."""

    @abstractmethod
    def choice(self, seq: Sequence[T]) -> T:
        """Choose one element from ``seq``."""


class RealEntropy(Entropy):
    """Entropy backed by ``secrets`` / ``random``.

    **Why this exists:** Production cryptographic-ish tokens via stdlib.
    """

    def randbytes(self, n: int) -> bytes:
        return secrets.token_bytes(n)

    def token_urlsafe(self, nbytes: int = 32) -> str:
        return secrets.token_urlsafe(nbytes)

    def choice(self, seq: Sequence[T]) -> T:
        return secrets.choice(seq)


class SyntheticEntropy(Entropy):
    """Seeded entropy for deterministic tests.

    **Why this exists:** Replayable nonces without patching ``secrets``.

    Example:
        >>> a = SyntheticEntropy(seed=7)
        >>> b = SyntheticEntropy(seed=7)
        >>> a.token_urlsafe(8) == b.token_urlsafe(8)
        True
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def randbytes(self, n: int) -> bytes:
        return bytes(self._rng.getrandbits(8) for _ in range(n))

    def token_urlsafe(self, nbytes: int = 32) -> str:
        import base64

        return base64.urlsafe_b64encode(self.randbytes(nbytes)).rstrip(b"=").decode("ascii")

    def choice(self, seq: Sequence[T]) -> T:
        return self._rng.choice(list(seq))


__all__ = ["Entropy", "RealEntropy", "SyntheticEntropy"]
