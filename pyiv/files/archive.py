"""Archive-backed filesystems (zip / tar as trees)."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path
from typing import BinaryIO, Iterator, Literal, Optional, Set, TextIO, Union

from pyiv.files._impl import Filesystem


def _norm(path: Union[str, Path]) -> str:
    s = str(path).replace("\\", "/")
    if not s.startswith("/"):
        s = "/" + s
    return s


def _member_name(norm_path: str) -> str:
    """Zip/tar member names are usually without leading slash."""
    return norm_path.lstrip("/")


class ZipFilesystem(Filesystem):
    """Treat a ZIP archive as a ``Filesystem`` tree (read; write when writable).

    **Why this exists:** Apps that read config or assets from a zip should inject
    the same ``Filesystem`` API as disk/memory, including under
    ``MountFilesystem``.

    Example:
        >>> import io, zipfile
        >>> from pyiv.files import ZipFilesystem
        >>> buf = io.BytesIO()
        >>> with zipfile.ZipFile(buf, "w") as zf:
        ...     zf.writestr("hello.txt", "hi")
        >>> fs = ZipFilesystem(buf.getvalue())
        >>> fs.read_text("/hello.txt")
        'hi'
    """

    def __init__(
        self, source: Union[str, Path, bytes], *, mode: Literal["r", "w", "x", "a"] = "r"
    ) -> None:
        """Open a zip from a path or in-memory bytes.

        Args:
            source: Path to a ``.zip`` file, or raw zip bytes
            mode: ``r`` (read-only) or ``a`` / ``w`` when ``source`` is a path
        """
        self._path: Optional[Path] = None
        if isinstance(source, (bytes, bytearray)):
            self._bytes_mode = True
            self._buf = io.BytesIO(bytes(source))
            zmode: Literal["r", "a"] = "a" if mode != "r" else "r"
            self._zf = zipfile.ZipFile(self._buf, zmode)
        else:
            self._bytes_mode = False
            self._path = Path(source)
            self._zf = zipfile.ZipFile(self._path, mode)
        self._writable = mode != "r"

    def _names(self) -> Set[str]:
        return set(self._zf.namelist())

    def open(
        self, file: Union[str, Path], mode: str = "r", encoding: Optional[str] = None
    ) -> Union[TextIO, BinaryIO]:
        name = _member_name(_norm(file))
        if "w" in mode or "a" in mode:
            if not self._writable:
                raise io.UnsupportedOperation("read-only zip filesystem")
            data = b""
            if "a" in mode and name in self._names():
                data = self._zf.read(name)
            if "b" in mode:
                return _ZipBytesIO(data, name, self)
            text = data.decode(encoding or "utf-8")
            return _ZipTextIO(text, name, self, encoding or "utf-8")
        if name not in self._names():
            raise FileNotFoundError(f"No such file: {file}")
        raw = self._zf.read(name)
        if "b" in mode:
            return io.BytesIO(raw)
        return io.StringIO(raw.decode(encoding or "utf-8"))

    def _write_member(self, name: str, data: bytes) -> None:
        # Replace member by rewriting is awkward; use writestr (may duplicate).
        # For tests, prefer MemoryFilesystem. Best-effort: writestr.
        self._zf.writestr(name, data)

    def exists(self, path: Union[str, Path]) -> bool:
        return self.is_file(path) or self.is_dir(path)

    def is_file(self, path: Union[str, Path]) -> bool:
        return _member_name(_norm(path)) in self._names()

    def is_dir(self, path: Union[str, Path]) -> bool:
        norm = _norm(path)
        if norm == "/":
            return True
        prefix = _member_name(norm).rstrip("/") + "/"
        return any(n.startswith(prefix) for n in self._names())

    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        if not self._writable:
            raise io.UnsupportedOperation("read-only zip filesystem")
        name = _member_name(_norm(path)).rstrip("/") + "/"
        if name in self._names() and not exist_ok:
            raise FileExistsError(path)
        self._zf.writestr(name, b"")

    def rmdir(self, path: Union[str, Path]) -> None:
        raise NotImplementedError("zip member removal is not supported")

    def unlink(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        raise NotImplementedError("zip member removal is not supported")

    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        return self.read_bytes(path).decode(encoding)

    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        self.write_bytes(path, content.encode(encoding))

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        name = _member_name(_norm(path))
        if name not in self._names():
            raise FileNotFoundError(f"No such file: {path}")
        return self._zf.read(name)

    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        if not self._writable:
            raise io.UnsupportedOperation("read-only zip filesystem")
        self._write_member(_member_name(_norm(path)), content)

    def listdir(self, path: Union[str, Path]) -> Iterator[str]:
        norm = _norm(path)
        prefix = "" if norm == "/" else _member_name(norm).rstrip("/") + "/"
        children = set()
        for name in self._names():
            if prefix and not name.startswith(prefix):
                continue
            rest = name[len(prefix) :]
            if not rest:
                continue
            children.add(rest.split("/")[0])
        return iter(sorted(children))

    def glob(self, pattern: Union[str, Path]) -> Iterator[Path]:
        import fnmatch

        pat = str(pattern)
        for name in self._names():
            full = "/" + name
            if fnmatch.fnmatch(full, pat) or fnmatch.fnmatch(name, pat):
                yield Path(full)

    def copy(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        self.write_bytes(dst, self.read_bytes(src))

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        raise NotImplementedError("zip move is not supported")

    def get_size(self, path: Union[str, Path]) -> int:
        return len(self.read_bytes(path))


class TarFilesystem(Filesystem):
    """Treat a tar archive as a read-oriented ``Filesystem`` tree.

    **Why this exists:** Same consumer API as disk/memory/zip for bundled trees.

    Example:
        >>> import io, tarfile
        >>> from pyiv.files import TarFilesystem
        >>> buf = io.BytesIO()
        >>> with tarfile.open(fileobj=buf, mode="w") as tf:
        ...     info = tarfile.TarInfo(name="a.txt")
        ...     data = b"x"
        ...     info.size = len(data)
        ...     tf.addfile(info, io.BytesIO(data))
        >>> fs = TarFilesystem(buf.getvalue())
        >>> fs.read_text("/a.txt")
        'x'
    """

    def __init__(self, source: Union[str, Path, bytes]) -> None:
        if isinstance(source, (bytes, bytearray)):
            self._bytes_mode = True
            self._buf = io.BytesIO(bytes(source))
            self._tf = tarfile.open(fileobj=self._buf, mode="r:*")
        else:
            self._bytes_mode = False
            self._tf = tarfile.open(name=str(source), mode="r:*")
        self._members = {m.name: m for m in self._tf.getmembers()}

    def open(
        self, file: Union[str, Path], mode: str = "r", encoding: Optional[str] = None
    ) -> Union[TextIO, BinaryIO]:
        if "w" in mode or "a" in mode:
            raise io.UnsupportedOperation("tar filesystem is read-only")
        raw = self.read_bytes(file)
        if "b" in mode:
            return io.BytesIO(raw)
        return io.StringIO(raw.decode(encoding or "utf-8"))

    def exists(self, path: Union[str, Path]) -> bool:
        return self.is_file(path) or self.is_dir(path)

    def is_file(self, path: Union[str, Path]) -> bool:
        name = _member_name(_norm(path))
        m = self._members.get(name)
        return bool(m and m.isfile())

    def is_dir(self, path: Union[str, Path]) -> bool:
        norm = _norm(path)
        if norm == "/":
            return True
        name = _member_name(norm)
        m = self._members.get(name)
        if m and m.isdir():
            return True
        prefix = name.rstrip("/") + "/"
        return any(n.startswith(prefix) for n in self._members)

    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        raise io.UnsupportedOperation("tar filesystem is read-only")

    def rmdir(self, path: Union[str, Path]) -> None:
        raise io.UnsupportedOperation("tar filesystem is read-only")

    def unlink(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        raise io.UnsupportedOperation("tar filesystem is read-only")

    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        return self.read_bytes(path).decode(encoding)

    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        raise io.UnsupportedOperation("tar filesystem is read-only")

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        name = _member_name(_norm(path))
        m = self._members.get(name)
        if not m or not m.isfile():
            raise FileNotFoundError(f"No such file: {path}")
        f = self._tf.extractfile(m)
        if f is None:
            raise FileNotFoundError(f"No such file: {path}")
        return f.read()

    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        raise io.UnsupportedOperation("tar filesystem is read-only")

    def listdir(self, path: Union[str, Path]) -> Iterator[str]:
        norm = _norm(path)
        prefix = "" if norm == "/" else _member_name(norm).rstrip("/") + "/"
        children = set()
        for name in self._members:
            if prefix and not name.startswith(prefix):
                continue
            rest = name[len(prefix) :]
            if not rest:
                continue
            children.add(rest.split("/")[0])
        return iter(sorted(children))

    def glob(self, pattern: Union[str, Path]) -> Iterator[Path]:
        import fnmatch

        pat = str(pattern)
        for name in self._members:
            full = "/" + name
            if fnmatch.fnmatch(full, pat) or fnmatch.fnmatch(name, pat):
                yield Path(full)

    def copy(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        raise io.UnsupportedOperation("tar filesystem is read-only")

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        raise io.UnsupportedOperation("tar filesystem is read-only")

    def get_size(self, path: Union[str, Path]) -> int:
        return len(self.read_bytes(path))


class _ZipBytesIO(io.BytesIO):
    def __init__(self, initial: bytes, name: str, fs: ZipFilesystem):
        super().__init__(initial)
        self._name = name
        self._fs = fs

    def close(self) -> None:
        if not self.closed:
            self.seek(0)
            self._fs._write_member(self._name, self.read())
        super().close()


class _ZipTextIO(io.StringIO):
    def __init__(self, initial: str, name: str, fs: ZipFilesystem, encoding: str):
        super().__init__(initial)
        self._name = name
        self._fs = fs
        self._encoding = encoding

    def close(self) -> None:
        if not self.closed:
            self.seek(0)
            self._fs._write_member(self._name, self.read().encode(self._encoding))
        super().close()
