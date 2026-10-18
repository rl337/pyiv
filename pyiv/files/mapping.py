"""Dict-backed virtual filesystem (``/proc``-style adapter example)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, Iterator, Mapping, MutableMapping, Optional, TextIO, Union

from pyiv.files._impl import Filesystem


class MappingFilesystem(Filesystem):
    """Expose a string→bytes (or str) mapping as a flat file tree under ``/``.

    **Why this exists:** Pattern for external adapters (DB row as ``/proc`` file)
    without putting SQL in core. Mount under ``MountFilesystem``.

    Example:
        >>> from pyiv.files import MappingFilesystem, MountFilesystem, MemoryFilesystem
        >>> proc = MappingFilesystem({"uptime": "1.0", "version": "pyiv"})
        >>> fs = MountFilesystem(MemoryFilesystem())
        >>> fs.mount("/proc", proc)
        >>> fs.read_text("/proc/uptime")
        '1.0'
    """

    def __init__(self, data: Optional[Mapping[str, Union[str, bytes]]] = None) -> None:
        self._data: MutableMapping[str, bytes] = {}
        if data:
            for key, value in data.items():
                name = key.lstrip("/")
                self._data[name] = value.encode("utf-8") if isinstance(value, str) else value

    def open(
        self, file: Union[str, Path], mode: str = "r", encoding: Optional[str] = None
    ) -> Union[TextIO, BinaryIO]:
        name = str(file).replace("\\", "/").lstrip("/")
        if "w" in mode or "a" in mode:
            existing = self._data.get(name, b"")
            if "a" not in mode:
                existing = b""
            if "b" in mode:
                return _MapBytesIO(existing, name, self)
            return _MapTextIO(existing.decode(encoding or "utf-8"), name, self, encoding or "utf-8")
        if name not in self._data:
            raise FileNotFoundError(file)
        raw = self._data[name]
        if "b" in mode:
            return io.BytesIO(raw)
        return io.StringIO(raw.decode(encoding or "utf-8"))

    def exists(self, path: Union[str, Path]) -> bool:
        name = str(path).replace("\\", "/").lstrip("/")
        return name == "" or name in self._data

    def is_file(self, path: Union[str, Path]) -> bool:
        name = str(path).replace("\\", "/").lstrip("/")
        return name in self._data

    def is_dir(self, path: Union[str, Path]) -> bool:
        name = str(path).replace("\\", "/").lstrip("/")
        return name == ""

    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        raise OSError("MappingFilesystem is a flat file tree")

    def rmdir(self, path: Union[str, Path]) -> None:
        raise OSError("MappingFilesystem is a flat file tree")

    def unlink(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        name = str(path).replace("\\", "/").lstrip("/")
        if name not in self._data:
            if missing_ok:
                return
            raise FileNotFoundError(path)
        del self._data[name]

    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        return self.read_bytes(path).decode(encoding)

    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        self.write_bytes(path, content.encode(encoding))

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        name = str(path).replace("\\", "/").lstrip("/")
        if name not in self._data:
            raise FileNotFoundError(path)
        return self._data[name]

    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        name = str(path).replace("\\", "/").lstrip("/")
        self._data[name] = content

    def listdir(self, path: Union[str, Path]) -> Iterator[str]:
        name = str(path).replace("\\", "/").lstrip("/")
        if name not in ("", "/"):
            raise FileNotFoundError(path)
        return iter(sorted(self._data.keys()))

    def glob(self, pattern: Union[str, Path]) -> Iterator[Path]:
        import fnmatch

        pat = str(pattern)
        for name in self._data:
            full = "/" + name
            if fnmatch.fnmatch(full, pat) or fnmatch.fnmatch(name, pat):
                yield Path(full)

    def copy(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        self.write_bytes(dst, self.read_bytes(src))

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        self.copy(src, dst)
        self.unlink(src)

    def get_size(self, path: Union[str, Path]) -> int:
        return len(self.read_bytes(path))


class _MapBytesIO(io.BytesIO):
    def __init__(self, initial: bytes, name: str, fs: MappingFilesystem):
        super().__init__(initial)
        self._name = name
        self._fs = fs

    def close(self) -> None:
        if not self.closed:
            self.seek(0)
            self._fs._data[self._name] = self.read()
        super().close()


class _MapTextIO(io.StringIO):
    def __init__(self, initial: str, name: str, fs: MappingFilesystem, encoding: str):
        super().__init__(initial)
        self._name = name
        self._fs = fs
        self._encoding = encoding

    def close(self) -> None:
        if not self.closed:
            self.seek(0)
            self._fs._data[self._name] = self.read().encode(self._encoding)
        super().close()
