"""Filesystem abstraction for dependency injection."""

import io
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Iterator, Optional, TextIO, Union


class Filesystem(ABC):
    """Abstract filesystem interface for file operations."""

    @abstractmethod
    def open(self, file: Union[str, Path], mode: str = "r", encoding: Optional[str] = None) -> Union[TextIO, BinaryIO]:
        """Open a file.

        Args:
            file: File path
            mode: File mode (r, w, a, rb, wb, etc.)
            encoding: Text encoding (for text modes)

        Returns:
            File handle
        """
        pass

    @abstractmethod
    def exists(self, path: Union[str, Path]) -> bool:
        """Check if a path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise
        """
        pass

    @abstractmethod
    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file.

        Args:
            path: Path to check

        Returns:
            True if path is a file, False otherwise
        """
        pass

    @abstractmethod
    def is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if path is a directory, False otherwise
        """
        pass

    @abstractmethod
    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory.

        Args:
            path: Directory path
            parents: Create parent directories if needed
            exist_ok: Don't raise error if directory exists
        """
        pass

    @abstractmethod
    def rmdir(self, path: Union[str, Path]) -> None:
        """Remove a directory.

        Args:
            path: Directory path
        """
        pass

    @abstractmethod
    def unlink(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        """Remove a file.

        Args:
            path: File path
            missing_ok: Don't raise error if file doesn't exist
        """
        pass

    @abstractmethod
    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        """Read text from a file.

        Args:
            path: File path
            encoding: Text encoding

        Returns:
            File contents as string
        """
        pass

    @abstractmethod
    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Write text to a file.

        Args:
            path: File path
            content: Text content to write
            encoding: Text encoding
        """
        pass

    @abstractmethod
    def read_bytes(self, path: Union[str, Path]) -> bytes:
        """Read bytes from a file.

        Args:
            path: File path

        Returns:
            File contents as bytes
        """
        pass

    @abstractmethod
    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        """Write bytes to a file.

        Args:
            path: File path
            content: Bytes content to write
        """
        pass

    @abstractmethod
    def listdir(self, path: Union[str, Path]) -> Iterator[str]:
        """List directory contents.

        Args:
            path: Directory path

        Yields:
            Directory entry names
        """
        pass

    @abstractmethod
    def glob(self, pattern: Union[str, Path]) -> Iterator[Path]:
        """Glob pattern matching.

        Args:
            pattern: Glob pattern

        Yields:
            Matching paths
        """
        pass

    @abstractmethod
    def copy(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Copy a file.

        Args:
            src: Source path
            dst: Destination path
        """
        pass

    @abstractmethod
    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move/rename a file or directory.

        Args:
            src: Source path
            dst: Destination path
        """
        pass

    @abstractmethod
    def get_size(self, path: Union[str, Path]) -> int:
        """Get file size in bytes.

        Args:
            path: File path

        Returns:
            File size in bytes
        """
        pass


class RealFilesystem(Filesystem):
    """Real filesystem implementation using standard library."""

    def open(self, file: Union[str, Path], mode: str = "r", encoding: Optional[str] = None) -> Union[TextIO, BinaryIO]:
        """Open a file using built-in open()."""
        if encoding is not None and "b" not in mode:
            return open(file, mode, encoding=encoding)  # type: ignore[return-value]
        return open(file, mode)  # type: ignore[return-value]

    def exists(self, path: Union[str, Path]) -> bool:
        """Check if path exists."""
        return Path(path).exists()

    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        return Path(path).is_file()

    def is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        return Path(path).is_dir()

    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory."""
        Path(path).mkdir(parents=parents, exist_ok=exist_ok)

    def rmdir(self, path: Union[str, Path]) -> None:
        """Remove a directory."""
        Path(path).rmdir()

    def unlink(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        """Remove a file."""
        Path(path).unlink(missing_ok=missing_ok)

    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        """Read text from a file."""
        return Path(path).read_text(encoding=encoding)

    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Write text to a file."""
        Path(path).write_text(content, encoding=encoding)

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        """Read bytes from a file."""
        return Path(path).read_bytes()

    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        """Write bytes to a file."""
        Path(path).write_bytes(content)

    def listdir(self, path: Union[str, Path]) -> Iterator[str]:
        """List directory contents."""
        return iter(os.listdir(path))

    def glob(self, pattern: Union[str, Path]) -> Iterator[Path]:
        """Glob pattern matching."""
        return Path(".").glob(str(pattern))

    def copy(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Copy a file."""
        shutil.copy(src, dst)

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move/rename a file or directory."""
        shutil.move(src, dst)

    def get_size(self, path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        return Path(path).stat().st_size


class MemoryFilesystem(Filesystem):
    """In-memory filesystem for testing."""

    def __init__(self):
        """Initialize in-memory filesystem."""
        self._files: dict[str, bytes] = {}
        self._dirs: set[str] = set()
        self._dirs.add("/")  # Root directory always exists

    def _normalize_path(self, path: Union[str, Path]) -> str:
        """Normalize path to string."""
        path_str = str(path)
        # Normalize separators
        path_str = path_str.replace("\\", "/")
        # Remove leading/trailing slashes except root
        if path_str.startswith("/"):
            return path_str
        return "/" + path_str.lstrip("/")

    def _ensure_parent_dir(self, path: str) -> None:
        """Ensure parent directory exists."""
        parent = "/".join(path.split("/")[:-1]) or "/"
        if parent not in self._dirs:
            self._dirs.add(parent)

    def open(self, file: Union[str, Path], mode: str = "r", encoding: Optional[str] = None) -> Union[TextIO, BinaryIO]:
        """Open a file in memory."""
        path = self._normalize_path(file)

        if "r" in mode:
            if path not in self._files:
                raise FileNotFoundError(f"No such file: {file}")
            content = self._files[path]
            if "b" in mode:
                return io.BytesIO(content)
            else:
                text = content.decode(encoding or "utf-8")
                return io.StringIO(text)
        elif "w" in mode or "a" in mode:
            if "a" in mode and path in self._files:
                existing = self._files[path]
            else:
                existing = b""

            self._ensure_parent_dir(path)

            if "b" in mode:
                stream: Union[_MemoryBytesIO, _MemoryTextIO] = _MemoryBytesIO(existing, path, self)
            else:
                text = existing.decode(encoding or "utf-8")
                stream = _MemoryTextIO(text, path, self, encoding or "utf-8")

            return stream
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def exists(self, path: Union[str, Path]) -> bool:
        """Check if path exists."""
        path_str = self._normalize_path(path)
        return path_str in self._files or path_str in self._dirs

    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        path_str = self._normalize_path(path)
        return path_str in self._files

    def is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        path_str = self._normalize_path(path)
        return path_str in self._dirs

    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory."""
        path_str = self._normalize_path(path)
        if path_str in self._dirs and not exist_ok:
            raise FileExistsError(f"Directory already exists: {path}")
        if path_str in self._files:
            raise FileExistsError(f"File exists at path: {path}")

        if parents:
            parts = path_str.split("/")
            for i in range(1, len(parts) + 1):
                parent = "/".join(parts[:i]) or "/"
                self._dirs.add(parent)
        else:
            parent = "/".join(path_str.split("/")[:-1]) or "/"
            if parent not in self._dirs:
                raise FileNotFoundError(f"Parent directory does not exist: {parent}")
            self._dirs.add(path_str)

    def rmdir(self, path: Union[str, Path]) -> None:
        """Remove a directory."""
        path_str = self._normalize_path(path)
        if path_str not in self._dirs:
            raise FileNotFoundError(f"Directory does not exist: {path}")
        if path_str == "/":
            raise ValueError("Cannot remove root directory")

        # Check if directory has children
        for file_path in self._files:
            if file_path.startswith(path_str + "/"):
                raise OSError(f"Directory not empty: {path}")
        for dir_path in self._dirs:
            if dir_path != path_str and dir_path.startswith(path_str + "/"):
                raise OSError(f"Directory not empty: {path}")

        self._dirs.remove(path_str)

    def unlink(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        """Remove a file."""
        path_str = self._normalize_path(path)
        if path_str not in self._files:
            if not missing_ok:
                raise FileNotFoundError(f"No such file: {path}")
            return
        del self._files[path_str]

    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        """Read text from a file."""
        path_str = self._normalize_path(path)
        if path_str not in self._files:
            raise FileNotFoundError(f"No such file: {path}")
        return self._files[path_str].decode(encoding)

    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Write text to a file."""
        path_str = self._normalize_path(path)
        self._ensure_parent_dir(path_str)
        self._files[path_str] = content.encode(encoding)

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        """Read bytes from a file."""
        path_str = self._normalize_path(path)
        if path_str not in self._files:
            raise FileNotFoundError(f"No such file: {path}")
        return self._files[path_str]

    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        """Write bytes to a file."""
        path_str = self._normalize_path(path)
        self._ensure_parent_dir(path_str)
        self._files[path_str] = content

    def listdir(self, path: Union[str, Path]) -> Iterator[str]:
        """List directory contents."""
        path_str = self._normalize_path(path)
        if path_str not in self._dirs:
            raise FileNotFoundError(f"No such directory: {path}")

        # Find direct children
        children = set()
        prefix = path_str if path_str == "/" else path_str + "/"

        for file_path in self._files:
            if file_path.startswith(prefix):
                rel_path = file_path[len(prefix) :]
                name = rel_path.split("/")[0]
                children.add(name)

        for dir_path in self._dirs:
            if dir_path != path_str and dir_path.startswith(prefix):
                rel_path = dir_path[len(prefix) :]
                name = rel_path.split("/")[0]
                children.add(name)

        return iter(sorted(children))

    def glob(self, pattern: Union[str, Path]) -> Iterator[Path]:
        """Glob pattern matching (simplified)."""
        import fnmatch

        pattern_str = str(pattern)

        # Simple glob implementation
        for file_path in self._files:
            if fnmatch.fnmatch(file_path, pattern_str):
                yield Path(file_path)

    def copy(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Copy a file."""
        src_str = self._normalize_path(src)
        dst_str = self._normalize_path(dst)

        if src_str not in self._files:
            raise FileNotFoundError(f"No such file: {src}")

        self._ensure_parent_dir(dst_str)
        self._files[dst_str] = self._files[src_str]

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move/rename a file or directory."""
        src_str = self._normalize_path(src)
        dst_str = self._normalize_path(dst)

        if src_str in self._files:
            self._ensure_parent_dir(dst_str)
            self._files[dst_str] = self._files[src_str]
            del self._files[src_str]
        elif src_str in self._dirs:
            # Move directory and all children
            self._ensure_parent_dir(dst_str)
            self._dirs.add(dst_str)
            self._dirs.remove(src_str)

            # Move all files in directory
            files_to_move = [f for f in self._files if f.startswith(src_str + "/")]
            for file_path in files_to_move:
                new_path = file_path.replace(src_str, dst_str, 1)
                self._files[new_path] = self._files[file_path]
                del self._files[file_path]

            # Move all subdirectories
            dirs_to_move = [d for d in self._dirs if d.startswith(src_str + "/")]
            for dir_path in dirs_to_move:
                new_path = dir_path.replace(src_str, dst_str, 1)
                self._dirs.add(new_path)
                self._dirs.remove(dir_path)
        else:
            raise FileNotFoundError(f"No such file or directory: {src}")

    def get_size(self, path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        path_str = self._normalize_path(path)
        if path_str not in self._files:
            raise FileNotFoundError(f"No such file: {path}")
        return len(self._files[path_str])


class _MemoryBytesIO(io.BytesIO):
    """BytesIO that writes back to MemoryFilesystem on close."""

    def __init__(self, initial_bytes: bytes, path: str, filesystem: "MemoryFilesystem"):
        """Initialize with path and filesystem reference."""
        super().__init__(initial_bytes)
        self._pyiv_path = path
        self._pyiv_filesystem = filesystem

    def close(self) -> None:
        """Write back to filesystem on close."""
        if not self.closed:
            self.seek(0)
            content = self.read()
            self._pyiv_filesystem._files[self._pyiv_path] = content
        super().close()


class _MemoryTextIO(io.StringIO):
    """StringIO that writes back to MemoryFilesystem on close."""

    def __init__(
        self,
        initial_value: str,
        path: str,
        filesystem: "MemoryFilesystem",
        encoding: str,
    ):
        """Initialize with path and filesystem reference."""
        super().__init__(initial_value)
        self._pyiv_path = path
        self._pyiv_filesystem = filesystem
        self._pyiv_encoding = encoding

    def close(self) -> None:
        """Write back to filesystem on close."""
        if not self.closed:
            self.seek(0)
            content = self.read()
            self._pyiv_filesystem._files[self._pyiv_path] = content.encode(self._pyiv_encoding)
        super().close()

    def exists(self, path: Union[str, Path]) -> bool:
        """Check if path exists."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        return path_str in self._pyiv_filesystem._files or path_str in self._pyiv_filesystem._dirs

    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        return path_str in self._pyiv_filesystem._files

    def is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        return path_str in self._pyiv_filesystem._dirs

    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        if path_str in self._pyiv_filesystem._dirs and not exist_ok:
            raise FileExistsError(f"Directory already exists: {path}")
        if path_str in self._pyiv_filesystem._files:
            raise FileExistsError(f"File exists at path: {path}")

        if parents:
            parts = path_str.split("/")
            for i in range(1, len(parts) + 1):
                parent = "/".join(parts[:i]) or "/"
                self._pyiv_filesystem._dirs.add(parent)
        else:
            parent = "/".join(path_str.split("/")[:-1]) or "/"
            if parent not in self._pyiv_filesystem._dirs:
                raise FileNotFoundError(f"Parent directory does not exist: {parent}")
            self._pyiv_filesystem._dirs.add(path_str)

    def rmdir(self, path: Union[str, Path]) -> None:
        """Remove a directory."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        if path_str not in self._pyiv_filesystem._dirs:
            raise FileNotFoundError(f"Directory does not exist: {path}")
        if path_str == "/":
            raise ValueError("Cannot remove root directory")

        # Check if directory has children
        for file_path in self._pyiv_filesystem._files:
            if file_path.startswith(path_str + "/"):
                raise OSError(f"Directory not empty: {path}")
        for dir_path in self._pyiv_filesystem._dirs:
            if dir_path != path_str and dir_path.startswith(path_str + "/"):
                raise OSError(f"Directory not empty: {path}")

        self._pyiv_filesystem._dirs.remove(path_str)

    def unlink(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        """Remove a file."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        if path_str not in self._pyiv_filesystem._files:
            if not missing_ok:
                raise FileNotFoundError(f"No such file: {path}")
            return
        del self._pyiv_filesystem._files[path_str]

    def read_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        """Read text from a file."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        if path_str not in self._pyiv_filesystem._files:
            raise FileNotFoundError(f"No such file: {path}")
        return self._pyiv_filesystem._files[path_str].decode(encoding)

    def write_text(self, path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Write text to a file."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        self._pyiv_filesystem._ensure_parent_dir(path_str)
        self._pyiv_filesystem._files[path_str] = content.encode(encoding)

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        """Read bytes from a file."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        if path_str not in self._pyiv_filesystem._files:
            raise FileNotFoundError(f"No such file: {path}")
        return self._pyiv_filesystem._files[path_str]

    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        """Write bytes to a file."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        self._pyiv_filesystem._ensure_parent_dir(path_str)
        self._pyiv_filesystem._files[path_str] = content

    def listdir(self, path: Union[str, Path]) -> Iterator[str]:
        """List directory contents."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        if path_str not in self._pyiv_filesystem._dirs:
            raise FileNotFoundError(f"No such directory: {path}")

        # Find direct children
        children = set()
        prefix = path_str if path_str == "/" else path_str + "/"

        for file_path in self._pyiv_filesystem._files:
            if file_path.startswith(prefix):
                rel_path = file_path[len(prefix) :]
                name = rel_path.split("/")[0]
                children.add(name)

        for dir_path in self._pyiv_filesystem._dirs:
            if dir_path != path_str and dir_path.startswith(prefix):
                rel_path = dir_path[len(prefix) :]
                name = rel_path.split("/")[0]
                children.add(name)

        return iter(sorted(children))

    def glob(self, pattern: Union[str, Path]) -> Iterator[Path]:
        """Glob pattern matching (simplified)."""
        import fnmatch

        pattern_str = str(pattern)

        # Simple glob implementation
        for file_path in self._pyiv_filesystem._files:
            if fnmatch.fnmatch(file_path, pattern_str):
                yield Path(file_path)

    def copy(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Copy a file."""
        src_str = self._pyiv_filesystem._normalize_path(src)
        dst_str = self._pyiv_filesystem._normalize_path(dst)

        if src_str not in self._pyiv_filesystem._files:
            raise FileNotFoundError(f"No such file: {src}")

        self._pyiv_filesystem._ensure_parent_dir(dst_str)
        self._pyiv_filesystem._files[dst_str] = self._pyiv_filesystem._files[src_str]

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move/rename a file or directory."""
        src_str = self._pyiv_filesystem._normalize_path(src)
        dst_str = self._pyiv_filesystem._normalize_path(dst)

        if src_str in self._pyiv_filesystem._files:
            self._pyiv_filesystem._ensure_parent_dir(dst_str)
            self._pyiv_filesystem._files[dst_str] = self._pyiv_filesystem._files[src_str]
            del self._pyiv_filesystem._files[src_str]
        elif src_str in self._pyiv_filesystem._dirs:
            # Move directory and all children
            self._pyiv_filesystem._ensure_parent_dir(dst_str)
            self._pyiv_filesystem._dirs.add(dst_str)
            self._pyiv_filesystem._dirs.remove(src_str)

            # Move all files in directory
            files_to_move = [f for f in self._pyiv_filesystem._files if f.startswith(src_str + "/")]
            for file_path in files_to_move:
                new_path = file_path.replace(src_str, dst_str, 1)
                self._pyiv_filesystem._files[new_path] = self._pyiv_filesystem._files[file_path]
                del self._pyiv_filesystem._files[file_path]

            # Move all subdirectories
            dirs_to_move = [d for d in self._pyiv_filesystem._dirs if d.startswith(src_str + "/")]
            for dir_path in dirs_to_move:
                new_path = dir_path.replace(src_str, dst_str, 1)
                self._pyiv_filesystem._dirs.add(new_path)
                self._pyiv_filesystem._dirs.remove(dir_path)
        else:
            raise FileNotFoundError(f"No such file or directory: {src}")

    def get_size(self, path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        path_str = self._pyiv_filesystem._normalize_path(path)
        if path_str not in self._pyiv_filesystem._files:
            raise FileNotFoundError(f"No such file: {path}")
        return len(self._pyiv_filesystem._files[path_str])
