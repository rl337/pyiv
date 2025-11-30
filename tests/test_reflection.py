"""Tests for reflection-based discovery in pyiv."""

from abc import ABC, abstractmethod
from typing import Any

import pytest

from pyiv import ReflectionConfig, SingletonType, get_injector
from pyiv.datetime_service import DateTimeService, MockDateTimeService, PythonDateTimeService
from pyiv.filesystem import Filesystem, MemoryFilesystem, RealFilesystem


# Test interfaces
class IService(ABC):
    """Test service interface."""
    
    @abstractmethod
    def do_something(self) -> str:
        pass


class IHandler(ABC):
    """Test handler interface."""
    
    @abstractmethod
    def handle(self, data: str) -> str:
        pass


# Test implementations in a test package structure
# We'll create these dynamically in tests


class TestReflectionConfig:
    """Tests for ReflectionConfig basic functionality."""
    
    def test_register_module_requires_type(self):
        """Test that register_module requires a type for interface."""
        config = ReflectionConfig()
        
        with pytest.raises(TypeError, match="interface must be a type"):
            config.register_module("not_a_type", "some.package")
    
    def test_register_module_invalid_package(self):
        """Test that register_module raises ImportError for invalid package."""
        config = ReflectionConfig()
        
        with pytest.raises(ImportError):
            config.register_module(IService, "nonexistent.package.that.does.not.exist")
    
    def test_discover_implementations_no_registration(self):
        """Test that discover_implementations returns empty dict if not registered."""
        config = ReflectionConfig()
        
        result = config.discover_implementations(IService)
        assert result == {}


class TestReflectionDiscovery:
    """Tests for reflection-based discovery."""
    
    def test_discover_implementations_in_package(self, tmp_path):
        """Test that implementations are discovered within the specified package."""
        # Create a test package structure
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        # Create a handler module
        handler_module = test_package_dir / "handlers.py"
        handler_module.write_text("""
from tests.test_reflection import IHandler

class CreateHandler(IHandler):
    def handle(self, data: str) -> str:
        return f"created: {data}"

class UpdateHandler(IHandler):
    def handle(self, data: str) -> str:
        return f"updated: {data}"
""")
        
        # Import the package
        import sys
        import importlib
        sys.path.insert(0, str(tmp_path))
        
        try:
            # Register and discover
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package.handlers",
                pattern="*Handler"
            )
            
            implementations = config.discover_implementations(IHandler)
            
            assert "CreateHandler" in implementations
            assert "UpdateHandler" in implementations
            assert len(implementations) == 2
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up module cache
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_discover_implementations_with_pattern(self, tmp_path):
        """Test that pattern matching filters discovered implementations."""
        # Create a test package
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        handler_module = test_package_dir / "handlers.py"
        handler_module.write_text("""
from tests.test_reflection import IHandler

class CreateHandler(IHandler):
    def handle(self, data: str) -> str:
        return "create"

class UpdateHandler(IHandler):
    def handle(self, data: str) -> str:
        return "update"

class NotAHandler:
    pass
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package.handlers",
                pattern="*Handler"
            )
            
            implementations = config.discover_implementations(IHandler)
            
            # Should only find classes matching *Handler pattern
            assert "CreateHandler" in implementations
            assert "UpdateHandler" in implementations
            assert "NotAHandler" not in implementations
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_discover_implementations_recursive(self, tmp_path):
        """Test that recursive discovery finds implementations in submodules."""
        # Create package structure
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        # Main module
        (test_package_dir / "handlers.py").write_text("""
from tests.test_reflection import IHandler

class MainHandler(IHandler):
    def handle(self, data: str) -> str:
        return "main"
""")
        
        # Submodule
        submodule_dir = test_package_dir / "submodule"
        submodule_dir.mkdir()
        (submodule_dir / "__init__.py").write_text("")
        (submodule_dir / "handlers.py").write_text("""
from tests.test_reflection import IHandler

class SubHandler(IHandler):
    def handle(self, data: str) -> str:
        return "sub"
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package",
                pattern="*Handler",
                recursive=True
            )
            
            implementations = config.discover_implementations(IHandler)
            
            # When registering at package level, submodules get prefixed
            # Check for MainHandler (could be "MainHandler" or "handlers.MainHandler")
            main_found = any("MainHandler" in name for name in implementations.keys())
            assert main_found, f"MainHandler not found in {list(implementations.keys())}"
            
            # Submodule class should be discovered - check for any name containing SubHandler
            submodule_found = any("SubHandler" in name for name in implementations.keys())
            assert submodule_found, f"SubHandler not found in {list(implementations.keys())}"
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_discover_implementations_no_recursive(self, tmp_path):
        """Test that non-recursive discovery only finds implementations in main module."""
        # Create package structure
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        # Main module
        (test_package_dir / "handlers.py").write_text("""
from tests.test_reflection import IHandler

class MainHandler(IHandler):
    def handle(self, data: str) -> str:
        return "main"
""")
        
        # Submodule
        submodule_dir = test_package_dir / "submodule"
        submodule_dir.mkdir()
        (submodule_dir / "__init__.py").write_text("")
        (submodule_dir / "handlers.py").write_text("""
from tests.test_reflection import IHandler

class SubHandler(IHandler):
    def handle(self, data: str) -> str:
        return "sub"
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package.handlers",
                pattern="*Handler",
                recursive=False
            )
            
            implementations = config.discover_implementations(IHandler)
            
            assert "MainHandler" in implementations
            # Submodule should not be discovered
            assert "SubHandler" not in implementations
            assert "submodule.handlers.SubHandler" not in implementations
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_discover_implementations_excludes_imported_classes(self, tmp_path):
        """Test that imported classes from other packages are not discovered."""
        # Create test package
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        handler_module = test_package_dir / "handlers.py"
        handler_module.write_text("""
from tests.test_reflection import IHandler
from pyiv.filesystem import RealFilesystem  # Import from another package

# This should be discovered (defined in this module)
class LocalHandler(IHandler):
    def handle(self, data: str) -> str:
        return "local"

# This should NOT be discovered (imported from elsewhere)
ImportedHandler = RealFilesystem
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package.handlers",
                pattern="*Handler"
            )
            
            implementations = config.discover_implementations(IHandler)
            
            # Should only find LocalHandler, not RealFilesystem
            assert "LocalHandler" in implementations
            assert len(implementations) == 1
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_discover_implementations_excludes_interface_itself(self, tmp_path):
        """Test that the interface class itself is not discovered."""
        # Create test package
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        handler_module = test_package_dir / "handlers.py"
        handler_module.write_text("""
from tests.test_reflection import IHandler

class CreateHandler(IHandler):
    def handle(self, data: str) -> str:
        return "create"
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package.handlers"
            )
            
            implementations = config.discover_implementations(IHandler)
            
            # IHandler itself should not be in the results
            assert IHandler not in implementations.values()
            assert "IHandler" not in implementations
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]


class TestReflectionWithExistingInterfaces:
    """Tests for discovering implementations of existing pyiv interfaces."""
    
    def test_discover_filesystem_implementations(self, tmp_path):
        """Test discovering Filesystem implementations from a package."""
        # Create test package with Filesystem implementations
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        fs_module = test_package_dir / "filesystems.py"
        fs_module.write_text("""
from pyiv.filesystem import Filesystem

class CustomFilesystem(Filesystem):
    def open(self, file, mode="r", encoding=None):
        return open(file, mode, encoding=encoding)
    
    def exists(self, path):
        return True
    
    def read(self, path, encoding=None):
        return "test"
    
    def write(self, path, content, encoding=None):
        pass
    
    def delete(self, path):
        pass
    
    def mkdir(self, path, parents=False):
        pass
    
    def listdir(self, path):
        return []
    
    def copy(self, src, dst):
        pass
    
    def move(self, src, dst):
        pass
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                Filesystem,
                "test_package.filesystems",
                pattern="*Filesystem"
            )
            
            implementations = config.discover_implementations(Filesystem)
            
            assert "CustomFilesystem" in implementations
            assert len(implementations) == 1
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_discover_datetime_service_implementations(self, tmp_path):
        """Test discovering DateTimeService implementations from a package."""
        # Create test package with DateTimeService implementations
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        dt_module = test_package_dir / "datetime_services.py"
        dt_module.write_text("""
from datetime import datetime, timezone
from pyiv.datetime_service import DateTimeService

class CustomDateTimeService(DateTimeService):
    def now_utc(self):
        return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    def now_utc_iso(self):
        return "2024-01-01T12:00:00+00:00"
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                DateTimeService,
                "test_package.datetime_services",
                pattern="*DateTimeService"
            )
            
            implementations = config.discover_implementations(DateTimeService)
            
            assert "CustomDateTimeService" in implementations
            assert len(implementations) == 1
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_discover_exports_existing_implementations(self, tmp_path):
        """Test that a package can export existing pyiv implementations."""
        # Create test package that re-exports existing implementations
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        exports_module = test_package_dir / "exports.py"
        exports_module.write_text("""
# Re-export existing pyiv implementations
from pyiv.filesystem import RealFilesystem, MemoryFilesystem
from pyiv.datetime_service import PythonDateTimeService, MockDateTimeService

# These are imported, not defined here, so they should NOT be discovered
# Only locally defined classes should be discovered
""")
        
        # Create a local implementation
        handlers_module = test_package_dir / "handlers.py"
        handlers_module.write_text("""
from pyiv.filesystem import Filesystem

class LocalFilesystem(Filesystem):
    def open(self, file, mode="r", encoding=None):
        return open(file, mode, encoding=encoding)
    
    def exists(self, path):
        return True
    
    def read(self, path, encoding=None):
        return ""
    
    def write(self, path, content, encoding=None):
        pass
    
    def delete(self, path):
        pass
    
    def mkdir(self, path, parents=False):
        pass
    
    def listdir(self, path):
        return []
    
    def copy(self, src, dst):
        pass
    
    def move(self, src, dst):
        pass
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                Filesystem,
                "test_package.handlers",
                pattern="*Filesystem"
            )
            
            implementations = config.discover_implementations(Filesystem)
            
            # Should only find LocalFilesystem (defined in the module)
            # Should NOT find RealFilesystem or MemoryFilesystem (imported)
            assert "LocalFilesystem" in implementations
            assert "RealFilesystem" not in implementations
            assert "MemoryFilesystem" not in implementations
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]


class TestInjectByName:
    """Tests for inject_by_name functionality."""
    
    def test_inject_by_name_basic(self, tmp_path):
        """Test basic inject_by_name functionality."""
        # Create test package
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        handler_module = test_package_dir / "handlers.py"
        handler_module.write_text("""
from tests.test_reflection import IHandler

class CreateHandler(IHandler):
    def handle(self, data: str) -> str:
        return f"created: {data}"
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package.handlers",
                pattern="*Handler"
            )
            
            injector = get_injector(config)
            
            # Get handler class by name
            handler_class = injector.inject_by_name(IHandler, "CreateHandler")
            
            assert handler_class.__name__ == "CreateHandler"
            assert issubclass(handler_class, IHandler)
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_inject_by_name_not_found(self, tmp_path):
        """Test that inject_by_name raises ValueError for unknown name."""
        # Create test package
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        handler_module = test_package_dir / "handlers.py"
        handler_module.write_text("""
from tests.test_reflection import IHandler

class CreateHandler(IHandler):
    def handle(self, data: str) -> str:
        return "create"
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package.handlers",
                pattern="*Handler"
            )
            
            injector = get_injector(config)
            
            with pytest.raises(ValueError, match="No implementation 'UnknownHandler' found"):
                injector.inject_by_name(IHandler, "UnknownHandler")
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]
    
    def test_inject_by_name_requires_reflection_config(self):
        """Test that inject_by_name requires ReflectionConfig."""
        from pyiv import Config, get_injector
        
        class RegularConfig(Config):
            def configure(self):
                pass
        
        injector = get_injector(RegularConfig)
        
        with pytest.raises(ValueError, match="does not support reflection-based discovery"):
            injector.inject_by_name(IService, "SomeService")
    
    def test_inject_by_name_with_singleton(self, tmp_path):
        """Test that inject_by_name works with singleton configuration."""
        # Create test package
        test_package_dir = tmp_path / "test_package"
        test_package_dir.mkdir()
        (test_package_dir / "__init__.py").write_text("")
        
        handler_module = test_package_dir / "handlers.py"
        handler_module.write_text("""
from tests.test_reflection import IHandler

class CreateHandler(IHandler):
    def __init__(self):
        self.calls = 0
    
    def handle(self, data: str) -> str:
        self.calls += 1
        return f"created: {data}"
""")
        
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            config = ReflectionConfig()
            config.register_module(
                IHandler,
                "test_package.handlers",
                pattern="*Handler",
                singleton_type=SingletonType.SINGLETON
            )
            
            injector = get_injector(config)
            
            # Get handler class
            handler_class = injector.inject_by_name(IHandler, "CreateHandler")
            
            # Get instances via interface (should be singleton)
            # When registered via reflection, injecting the interface should return the singleton
            instance1 = injector.inject(IHandler)
            instance2 = injector.inject(IHandler)
            
            # Should be the same instance
            assert instance1 is instance2
            assert isinstance(instance1, handler_class)
            
            # Verify it works
            result = instance1.handle("test")
            assert result == "created: test"
            assert instance1.calls == 1
            assert instance2.calls == 1  # Same instance
        finally:
            sys.path.remove(str(tmp_path))
            modules_to_remove = [m for m in sys.modules.keys() if m.startswith("test_package")]
            for m in modules_to_remove:
                del sys.modules[m]

