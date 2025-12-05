"""Tests for nested submodule path handling in reflection discovery."""

import sys
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import pytest

from pyiv import ReflectionConfig


class Service(ABC):
    """Test service interface."""

    @abstractmethod
    def do_something(self) -> str:
        pass


def test_nested_submodules_preserve_full_path(tmp_path):
    """Test that nested submodules preserve full path to avoid name collisions."""
    # Create package structure:
    # test_pkg/
    #   mod.py (contains ClassA)
    #   sub/
    #     mod.py (contains ClassA)

    test_package_dir = tmp_path / "test_pkg"
    test_package_dir.mkdir()
    (test_package_dir / "__init__.py").write_text("")

    # Top-level mod.py
    (test_package_dir / "mod.py").write_text(
        """
from tests.test_reflection_nested_paths import Service

class ClassA(Service):
    def do_something(self) -> str:
        return "top_level"
"""
    )

    # Nested sub/mod.py
    sub_dir = test_package_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "__init__.py").write_text("")
    (sub_dir / "mod.py").write_text(
        """
from tests.test_reflection_nested_paths import Service

class ClassA(Service):
    def do_something(self) -> str:
        return "nested"
"""
    )

    sys.path.insert(0, str(tmp_path))

    try:
        config = ReflectionConfig()
        config.register_module(Service, "test_pkg", recursive=True)

        implementations = config.discover_implementations(Service)

        # Should have both ClassA implementations with different paths
        assert len(implementations) == 2

        # Check that both are present with full paths
        # Top-level: "mod.ClassA"
        # Nested: "sub.mod.ClassA"
        assert "mod.ClassA" in implementations
        assert "sub.mod.ClassA" in implementations

        # Verify they're different classes
        top_class = implementations["mod.ClassA"]
        nested_class = implementations["sub.mod.ClassA"]
        assert top_class is not nested_class

        # Verify they work correctly
        top_instance = top_class()
        nested_instance = nested_class()
        assert top_instance.do_something() == "top_level"
        assert nested_instance.do_something() == "nested"

    finally:
        sys.path.remove(str(tmp_path))
        modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_pkg")]
        for m in modules_to_remove:
            del sys.modules[m]


def test_deeply_nested_submodules(tmp_path):
    """Test that deeply nested submodules preserve full path."""
    # Create package structure:
    # test_pkg/
    #   a/
    #     b/
    #       handler.py (contains Handler)

    test_package_dir = tmp_path / "test_pkg"
    test_package_dir.mkdir()
    (test_package_dir / "__init__.py").write_text("")

    a_dir = test_package_dir / "a"
    a_dir.mkdir()
    (a_dir / "__init__.py").write_text("")

    b_dir = a_dir / "b"
    b_dir.mkdir()
    (b_dir / "__init__.py").write_text("")
    (b_dir / "handler.py").write_text(
        """
from tests.test_reflection_nested_paths import Service

class Handler(Service):
    def do_something(self) -> str:
        return "deep"
"""
    )

    sys.path.insert(0, str(tmp_path))

    try:
        config = ReflectionConfig()
        config.register_module(Service, "test_pkg", recursive=True)

        implementations = config.discover_implementations(Service)

        # Should find Handler with full path
        assert "a.b.handler.Handler" in implementations

        handler_class = implementations["a.b.handler.Handler"]
        instance = handler_class()
        assert instance.do_something() == "deep"

    finally:
        sys.path.remove(str(tmp_path))
        modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_pkg")]
        for m in modules_to_remove:
            del sys.modules[m]


def test_same_class_name_different_paths(tmp_path):
    """Test that same class name in different paths doesn't collide."""
    # Create package structure:
    # test_pkg/
    #   handlers/
    #     create.py (contains CreateHandler)
    #   api/
    #     handlers/
    #       create.py (contains CreateHandler)

    test_package_dir = tmp_path / "test_pkg"
    test_package_dir.mkdir()
    (test_package_dir / "__init__.py").write_text("")

    # First handlers/create.py
    handlers1_dir = test_package_dir / "handlers"
    handlers1_dir.mkdir()
    (handlers1_dir / "__init__.py").write_text("")
    (handlers1_dir / "create.py").write_text(
        """
from tests.test_reflection_nested_paths import Service

class CreateHandler(Service):
    def do_something(self) -> str:
        return "handlers_create"
"""
    )

    # Second api/handlers/create.py
    api_dir = test_package_dir / "api"
    api_dir.mkdir()
    (api_dir / "__init__.py").write_text("")

    handlers2_dir = api_dir / "handlers"
    handlers2_dir.mkdir()
    (handlers2_dir / "__init__.py").write_text("")
    (handlers2_dir / "create.py").write_text(
        """
from tests.test_reflection_nested_paths import Service

class CreateHandler(Service):
    def do_something(self) -> str:
        return "api_handlers_create"
"""
    )

    sys.path.insert(0, str(tmp_path))

    try:
        config = ReflectionConfig()
        config.register_module(Service, "test_pkg", recursive=True)

        implementations = config.discover_implementations(Service)

        # Should have both CreateHandler implementations with different paths
        assert len(implementations) == 2

        # Check that both are present with full paths
        assert "handlers.create.CreateHandler" in implementations
        assert "api.handlers.create.CreateHandler" in implementations

        # Verify they're different classes
        handler1 = implementations["handlers.create.CreateHandler"]
        handler2 = implementations["api.handlers.create.CreateHandler"]
        assert handler1 is not handler2

        # Verify they work correctly
        instance1 = handler1()
        instance2 = handler2()
        assert instance1.do_something() == "handlers_create"
        assert instance2.do_something() == "api_handlers_create"

    finally:
        sys.path.remove(str(tmp_path))
        modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_pkg")]
        for m in modules_to_remove:
            del sys.modules[m]
