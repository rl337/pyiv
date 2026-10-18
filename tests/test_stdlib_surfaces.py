"""Tests for process / log / entropy / hashing / time package surfaces."""

import argparse

from pyiv.entropy import SyntheticEntropy
from pyiv.hashing import RealHasher, SyntheticHasher
from pyiv.log import (
    LogOptions,
    LogSetup,
    MemoryLogger,
    MemoryLoggerFactory,
    add_logging_args,
    log_options_from_args,
)
from pyiv.process import MemoryArgv, MemoryEnvironment, MemoryProcessRunner
from pyiv.time import SyntheticClock


def test_time_package_clock():
    clock = SyntheticClock(start_time=10.0)
    clock.advance(2.0)
    assert clock.time() == 12.0


def test_memory_environment():
    env = MemoryEnvironment({"A": "1"})
    env.set("B", "2")
    assert env.get("A") == "1"
    assert env.as_dict()["B"] == "2"


def test_memory_process_runner():
    runner = MemoryProcessRunner()
    runner.script(["echo"], returncode=0, stdout="hi\n")
    result = runner.run(["echo", "x"])
    assert result.stdout == "hi\n"
    assert runner.calls[0] == ("echo", "x")


def test_memory_argv_exit():
    argv = MemoryArgv(["tool", "-v"])
    argv.exit(3)
    assert argv.exited
    assert argv.exit_status.code == 3


def test_log_options_from_args():
    p = argparse.ArgumentParser()
    add_logging_args(p)
    ns = p.parse_args(["-v", "--log-format", "long"])
    opts = log_options_from_args(ns)
    assert opts.effective_level() == "INFO"
    assert opts.format_style == "long"


def test_memory_logger_and_factory():
    factory = MemoryLoggerFactory()
    log = factory.get("svc")
    assert isinstance(log, MemoryLogger)
    log.info("hello %s", "world")
    assert log.records[0].message == "hello world"


def test_log_setup_apply():
    import io
    import logging

    stream = io.StringIO()
    LogSetup(stream=stream).apply(LogOptions(level="INFO", verbose=0))
    logging.getLogger("pyiv.testsetup").info("ping")
    assert "ping" in stream.getvalue()


def test_entropy_and_hasher():
    e1 = SyntheticEntropy(seed=1)
    e2 = SyntheticEntropy(seed=1)
    assert e1.token_urlsafe(8) == e2.token_urlsafe(8)
    assert RealHasher().digest("sha256", b"abc").hex().startswith("ba7816bf")
    fixed = SyntheticHasher(fixed=b"\x00\x01")
    assert fixed.digest("sha256", b"x") == b"\x00\x01"
