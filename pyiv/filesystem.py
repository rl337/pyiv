"""Compatibility re-exports for ``pyiv.files``.

Prefer ``from pyiv.files import Filesystem, MemoryFilesystem, ...``.
"""

from pyiv.files import Filesystem, MemoryFilesystem, RealFilesystem

__all__ = ["Filesystem", "RealFilesystem", "MemoryFilesystem"]
