"""Tests for MountFilesystem, Zip/Tar, MappingFilesystem."""

import io
import tarfile
import zipfile

import pytest

from pyiv.files import (
    MappingFilesystem,
    MemoryFilesystem,
    MountFilesystem,
    TarFilesystem,
    ZipFilesystem,
)


def test_mount_routes_to_nested_fs():
    root = MemoryFilesystem()
    root.write_text("/data/a.txt", "a")
    proc = MappingFilesystem({"status": "ok"})
    fs = MountFilesystem(root)
    fs.mount("/proc", proc)
    assert fs.read_text("/data/a.txt") == "a"
    assert fs.read_text("/proc/status") == "ok"
    assert "proc" in list(fs.listdir("/"))
    assert "status" in list(fs.listdir("/proc"))


def test_zip_filesystem_read():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hello.txt", "hi")
    fs = ZipFilesystem(buf.getvalue())
    assert fs.read_text("/hello.txt") == "hi"
    assert "hello.txt" in list(fs.listdir("/"))


def test_tar_filesystem_read():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo(name="a.txt")
        data = b"x"
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    fs = TarFilesystem(buf.getvalue())
    assert fs.read_text("/a.txt") == "x"


def test_memory_open_writeback():
    fs = MemoryFilesystem()
    with fs.open("/w.txt", "w") as f:
        f.write("hello")
    assert fs.read_text("/w.txt") == "hello"


def test_compat_reexport():
    from pyiv.filesystem import MemoryFilesystem as MF

    assert MF is MemoryFilesystem
