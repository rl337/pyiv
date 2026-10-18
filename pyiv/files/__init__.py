"""Use-case package for injectable filesystem surfaces.

Groups path I/O, mounts, and archive-as-tree adapters under one purpose —
not a mirror of ``os`` / ``io`` / ``pathlib`` module names.

**What Problem Does This Solve?**

File APIs are spread across the stdlib and hard to mock without residue.
Inject ``Filesystem`` and bind ``RealFilesystem``, ``MemoryFilesystem``,
``MountFilesystem``, or archive-backed trees.

**Real-World Use Cases:**
- Unit tests with ``MemoryFilesystem`` (no disk)
- Mount a fake ``/proc`` via ``MappingFilesystem`` + ``MountFilesystem``
- Read assets from zip/tar with the same consumer API

Architecture:
 - ``Filesystem`` / ``RealFilesystem`` / ``MemoryFilesystem``
 - ``MountFilesystem`` / ``MountPoint``
 - ``ZipFilesystem`` / ``TarFilesystem``
 - ``MappingFilesystem`` (dict-backed virtual tree adapter)

Example:
    >>> from pyiv.files import MemoryFilesystem, MountFilesystem, MappingFilesystem
    >>> root = MemoryFilesystem()
    >>> root.write_text("/app/config.txt", "x=1")
    >>> fs = MountFilesystem(root)
    >>> fs.mount("/proc", MappingFilesystem({"uptime": "0.1"}))
    >>> fs.read_text("/app/config.txt")
    'x=1'
    >>> fs.read_text("/proc/uptime")
    '0.1'
"""

from pyiv.files._impl import Filesystem, MemoryFilesystem, RealFilesystem
from pyiv.files.archive import TarFilesystem, ZipFilesystem
from pyiv.files.mapping import MappingFilesystem
from pyiv.files.mount import MountFilesystem, MountPoint

__all__ = [
    "Filesystem",
    "RealFilesystem",
    "MemoryFilesystem",
    "MountFilesystem",
    "MountPoint",
    "ZipFilesystem",
    "TarFilesystem",
    "MappingFilesystem",
]
