"""Tests for re-exported classes to ensure they're only discovered once."""

import sys
from abc import ABC, abstractmethod
from pathlib import Path

import pytest

from pyiv import ReflectionConfig


class Service(ABC):
    """Test service interface."""

    @abstractmethod
    def do_something(self) -> str:
        pass


def test_re_exported_class_only_discovered_once(tmp_path):
    """Test that a class imported and re-exported is only discovered once."""
    # Create package structure:
    # test_pkg/
    #   handlers/
    #     local.py (contains LocalHandler - defined here)
    #   exports.py (imports and re-exports LocalHandler)

    test_package_dir = tmp_path / "test_pkg"
    test_package_dir.mkdir()
    (test_package_dir / "__init__.py").write_text("")

    # handlers/local.py - defines LocalHandler
    handlers_dir = test_package_dir / "handlers"
    handlers_dir.mkdir()
    (handlers_dir / "__init__.py").write_text("")
    (handlers_dir / "local.py").write_text(
        """
from tests.test_reflection_re_export import Service

class LocalHandler(Service):
    def do_something(self) -> str:
        return "local"
"""
    )

    # exports.py - imports and re-exports LocalHandler
    (test_package_dir / "exports.py").write_text(
        """
from tests.test_reflection_re_export import Service
from test_pkg.handlers.local import LocalHandler

# Re-export
__all__ = ["LocalHandler"]
"""
    )

    sys.path.insert(0, str(tmp_path))

    try:
        config = ReflectionConfig()
        config.register_module(Service, "test_pkg", recursive=True)

        implementations = config.discover_implementations(Service)

        # Should only discover LocalHandler once, from handlers.local where it's defined
        # Not from exports.py where it's re-exported
        assert len(implementations) == 1
        assert "handlers.local.LocalHandler" in implementations
        assert "exports.LocalHandler" not in implementations

        # Verify it works
        handler_class = implementations["handlers.local.LocalHandler"]
        instance = handler_class()
        assert instance.do_something() == "local"

    finally:
        sys.path.remove(str(tmp_path))
        modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_pkg")]
        for m in modules_to_remove:
            del sys.modules[m]


def test_multiple_re_exports_only_discovered_once(tmp_path):
    """Test that a class re-exported in multiple modules is only discovered once."""
    # Create package structure:
    # test_pkg/
    #   core/
    #     service.py (contains Service - defined here)
    #   api/
    #     __init__.py (re-exports Service)
    #   handlers/
    #     __init__.py (re-exports Service)

    test_package_dir = tmp_path / "test_pkg"
    test_package_dir.mkdir()
    (test_package_dir / "__init__.py").write_text("")

    # core/service.py - defines Service
    core_dir = test_package_dir / "core"
    core_dir.mkdir()
    (core_dir / "__init__.py").write_text("")
    (core_dir / "service.py").write_text(
        """
from tests.test_reflection_re_export import Service

class Service(Service):
    def do_something(self) -> str:
        return "service"
"""
    )

    # api/__init__.py - re-exports Service
    api_dir = test_package_dir / "api"
    api_dir.mkdir()
    (api_dir / "__init__.py").write_text(
        """
from test_pkg.core.service import Service

__all__ = ["Service"]
"""
    )

    # handlers/__init__.py - also re-exports Service
    handlers_dir = test_package_dir / "handlers"
    handlers_dir.mkdir()
    (handlers_dir / "__init__.py").write_text(
        """
from test_pkg.core.service import Service

__all__ = ["Service"]
"""
    )

    sys.path.insert(0, str(tmp_path))

    try:
        config = ReflectionConfig()
        config.register_module(Service, "test_pkg", recursive=True)

        implementations = config.discover_implementations(Service)

        # Should only discover Service once, from core.service where it's defined
        assert len(implementations) == 1
        assert "core.service.Service" in implementations
        assert "api.Service" not in implementations
        assert "handlers.Service" not in implementations

        # Verify it works
        service_class = implementations["core.service.Service"]
        instance = service_class()
        assert instance.do_something() == "service"

    finally:
        sys.path.remove(str(tmp_path))
        modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_pkg")]
        for m in modules_to_remove:
            del sys.modules[m]
