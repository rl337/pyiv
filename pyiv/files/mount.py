"""Composite filesystem that mounts other filesystems at path prefixes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator, List, Optional, Set, TextIO, Tuple, Union

from pyiv.files._impl import Filesystem


@dataclass(frozen=True)
class MountPoint:
    """A path prefix bound to a nested filesystem.

    **Why this exists:** Frozen knob for mount tables (Settings-friendly).

    Example:
        >>> from pyiv.files import MemoryFilesystem, MountPoint
        >>> MountPoint("/proc", MemoryFilesystem()).mount_path
        '/proc'
    """

    mount_path: str
    filesystem: Filesystem

    def __post_init__(self) -> None:
        path = str(self.mount_path).replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        path = path.rstrip("/") or "/"
        object.__setattr__(self, "mount_path", path)


class MountFilesystem(Filesystem):
    """Path-prefix router over nested ``Filesystem`` instances.

    **Why this exists:** Expose virtual trees (fake ``/proc``, zip mounts, etc.)
    beside a real or memory root without monkeypatching ``open``.

    Example:
        >>> from pyiv.files import MemoryFilesystem, MountFilesystem
        >>> root = MemoryFilesystem()
        >>> root.write_text("/data/a.txt", "a")
        >>> proc = MemoryFilesystem()
        >>> proc.write_text("/status", "ok")
        >>> fs = MountFilesystem(root)
        >>> fs.mount("/proc", proc)
        >>> fs.read_text("/data/a.txt")
        'a'
        >>> fs.read_text("/proc/status")
        'ok'
    """

    def __init__(self, root: Optional[Filesystem] = None) -> None:
        from pyiv.files._impl import MemoryFilesystem

        self._root: Filesystem = root if root is not None else MemoryFilesystem()
        self._mounts: List[MountPoint] = []

    def mount(self, mount_path: Union[str, Path], filesystem: Filesystem) -> None:
        """Mount ``filesystem`` at ``mount_path`` (longest prefix wins)."""
        point = MountPoint(str(mount_path), filesystem)
        self._mounts = [m for m in self._mounts if m.mount_path != point.mount_path]
        self._mounts.append(point)
        self._mounts.sort(key=lambda m: len(m.mount_path), reverse=True)

    def unmount(self, mount_path: Union[str, Path]) -> None:
        """Remove a mount by path prefix."""
        path = MountPoint(str(mount_path), self._root).mount_path
        self._mounts = [m for m in self._mounts if m.mount_path != path]

    def _resolve(self, path: Union[str, Path]) -> Tuple[Filesystem, str]:
        """Return (filesystem, path-relative-to-that-fs)."""
        norm = str(path).replace("\\", "/")
        if not norm.startswith("/"):
            norm = "/" + norm
        for mount in self._mounts:
            prefix = mount.mount_path
            if norm == prefix or norm.startswith(prefix + "/"):
                rel = norm[len(prefix) :] or "/"
                if not rel.startswith("/"):
                    rel = "/" + rel
                return mount.filesystem, rel
        return self._root, norm

    def open(
        self, file: Union[str, Path], mode: str = "r", encoding: Optional[str] = None
    ) -> Union[TextIO, BinaryIO]:
        fs, rel = self._resolve(file)
        return fs.open(rel, mode=mode, encoding=encoding)

    def exists(self, path: Union[str, Path]) -> bool:
        fs, rel = self._resolve(path)
        return fs.exists(rel)

    def is_file(self, path: Union[str, Path]) -> bool:
        fs, rel = self._resolve(path)
        return fs.is_file(rel)

    def is_dir(self, path: Union[str, Path]) -> bool:
        norm = str(path).replace("\\", "/")
        if not norm.startswith("/"):
            norm = "/" + norm
        for mount in self._mounts:
            if mount.mount_path == norm or mount.mount_path.startswith(norm.rstrip("/") + "/"):
                return True
        fs, rel = self._resolve(path)
        return fs.is_dir(rel)

    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        fs, rel = self._resolve(path)
        fs.mkdir(rel, parents=parents, exist_ok=exist_ok)

    def rmdir(self, path: Union[str, Path]) -> None:
        fs, rel = self._resolve(path)
        fs.rmdir(rel)

    def unlink(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        fs, rel = self._resolve(path)
        fs.unlink(rel, missing_ok=missing_ok)

    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        fs, rel = self._resolve(path)
        return fs.read_text(rel, encoding=encoding)

    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        fs, rel = self._resolve(path)
        fs.write_text(rel, content, encoding=encoding)

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        fs, rel = self._resolve(path)
        return fs.read_bytes(rel)

    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        fs, rel = self._resolve(path)
        fs.write_bytes(rel, content)

    def listdir(self, path: Union[str, Path]) -> Iterator[str]:
        norm = str(path).replace("\\", "/")
        if not norm.startswith("/"):
            norm = "/" + norm
        names: Set[str] = set()
        fs, rel = self._resolve(path)
        if fs.is_dir(rel) or fs.exists(rel):
            names.update(fs.listdir(rel))
        prefix = norm.rstrip("/")
        for mount in self._mounts:
            mp = mount.mount_path
            if prefix == "/":
                # top-level mount name
                child = mp.lstrip("/").split("/")[0]
                if child:
                    names.add(child)
            elif mp.startswith(prefix + "/"):
                rest = mp[len(prefix) + 1 :]
                child = rest.split("/")[0]
                if child:
                    names.add(child)
        return iter(sorted(names))

    def glob(self, pattern: Union[str, Path]) -> Iterator[Path]:
        # Delegate to root + remount results under each mount prefix
        for p in self._root.glob(pattern):
            yield p
        for mount in self._mounts:
            for p in mount.filesystem.glob(pattern):
                joined = mount.mount_path.rstrip("/") + str(p)
                yield Path(joined)

    def copy(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        data = self.read_bytes(src)
        self.write_bytes(dst, data)

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        self.copy(src, dst)
        if self.is_file(src):
            self.unlink(src)
        else:
            self.rmdir(src)

    def get_size(self, path: Union[str, Path]) -> int:
        fs, rel = self._resolve(path)
        return fs.get_size(rel)
