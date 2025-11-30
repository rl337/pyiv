"""Tests for Filesystem abstraction."""

from pathlib import Path

import pytest

from pyiv.filesystem import Filesystem, MemoryFilesystem, RealFilesystem


def test_real_filesystem_exists(tmp_path):
    """Test RealFilesystem.exists()."""
    fs = RealFilesystem()

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    assert fs.exists(test_file) is True
    assert fs.exists(tmp_path / "nonexistent.txt") is False


def test_real_filesystem_read_write(tmp_path):
    """Test RealFilesystem read/write operations."""
    fs = RealFilesystem()

    test_file = tmp_path / "test.txt"
    fs.write_text(test_file, "hello world")

    assert fs.read_text(test_file) == "hello world"
    assert fs.is_file(test_file) is True


def test_memory_filesystem_basic():
    """Test basic MemoryFilesystem operations."""
    fs = MemoryFilesystem()

    # Write and read text
    fs.write_text("/test.txt", "hello world")
    assert fs.read_text("/test.txt") == "hello world"
    assert fs.exists("/test.txt") is True
    assert fs.is_file("/test.txt") is True


def test_memory_filesystem_bytes():
    """Test MemoryFilesystem byte operations."""
    fs = MemoryFilesystem()

    content = b"binary data\x00\x01\x02"
    fs.write_bytes("/test.bin", content)
    assert fs.read_bytes("/test.bin") == content


def test_memory_filesystem_directories():
    """Test MemoryFilesystem directory operations."""
    fs = MemoryFilesystem()

    fs.mkdir("/test_dir")
    assert fs.is_dir("/test_dir") is True
    assert fs.exists("/test_dir") is True

    fs.write_text("/test_dir/file.txt", "content")
    assert fs.exists("/test_dir/file.txt") is True


def test_memory_filesystem_listdir():
    """Test MemoryFilesystem listdir."""
    fs = MemoryFilesystem()

    fs.mkdir("/test_dir")
    fs.write_text("/test_dir/file1.txt", "content1")
    fs.write_text("/test_dir/file2.txt", "content2")
    fs.mkdir("/test_dir/subdir")

    entries = list(fs.listdir("/test_dir"))
    assert set(entries) == {"file1.txt", "file2.txt", "subdir"}


def test_memory_filesystem_copy_move():
    """Test MemoryFilesystem copy and move."""
    fs = MemoryFilesystem()

    fs.write_text("/source.txt", "content")
    fs.copy("/source.txt", "/dest.txt")

    assert fs.read_text("/source.txt") == "content"
    assert fs.read_text("/dest.txt") == "content"

    fs.move("/source.txt", "/moved.txt")
    assert fs.exists("/source.txt") is False
    assert fs.read_text("/moved.txt") == "content"


def test_memory_filesystem_open():
    """Test MemoryFilesystem open() method."""
    fs = MemoryFilesystem()

    # Write mode
    with fs.open("/test.txt", "w") as f:
        f.write("hello")

    # Read mode
    with fs.open("/test.txt", "r") as f:
        content = f.read()
        assert content == "hello"


def test_memory_filesystem_errors():
    """Test MemoryFilesystem error handling."""
    fs = MemoryFilesystem()

    # Read non-existent file
    with pytest.raises(FileNotFoundError):
        fs.read_text("/nonexistent.txt")

    # Remove non-existent file
    with pytest.raises(FileNotFoundError):
        fs.unlink("/nonexistent.txt")

    # Remove non-existent file with missing_ok
    fs.unlink("/nonexistent.txt", missing_ok=True)  # Should not raise


def test_memory_filesystem_mkdir_parents():
    """Test MemoryFilesystem mkdir with parents."""
    fs = MemoryFilesystem()

    fs.mkdir("/a/b/c", parents=True)
    assert fs.is_dir("/a") is True
    assert fs.is_dir("/a/b") is True
    assert fs.is_dir("/a/b/c") is True
