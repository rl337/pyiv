"""Pytest configuration and fixtures."""

import os
import pty
import sys

import pytest


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "tty: mark test as requiring TTY (will use PTY for testing)")
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture(autouse=True)
def _clear_global_singletons():
    """Reset process-wide singleton caches between tests."""
    from pyiv.scope import GlobalSingletonScope
    from pyiv.singleton import GlobalSingletonRegistry

    GlobalSingletonRegistry.clear()
    GlobalSingletonScope.clear()
    yield
    GlobalSingletonRegistry.clear()
    GlobalSingletonScope.clear()


@pytest.fixture(scope="session")
def has_tty():
    """Check if TTY is available."""
    return sys.stdout.isatty()


@pytest.fixture
def pty_context():
    """Create PTY context for testing - always available.

    Yields:
        Tuple of (master_fd, slave_stream) for testing terminal functionality
    """
    master_fd, slave_fd = pty.openpty()
    slave_stream = os.fdopen(slave_fd, "w")

    yield master_fd, slave_stream

    os.close(master_fd)
    slave_stream.close()
