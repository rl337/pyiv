"""Tests for singleton support."""

import threading
from abc import ABC, abstractmethod

import pytest

from pyiv import Config, GlobalSingletonRegistry, Injector, SingletonType, get_injector


class Database(ABC):
    """Abstract database interface."""

    @abstractmethod
    def query(self, sql: str) -> str:
        pass


class Logger(ABC):
    """Abstract logger interface."""

    @abstractmethod
    def log(self, message: str) -> None:
        pass


class PostgreSQL(Database):
    """PostgreSQL database implementation."""

    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port
        self._instance_id = id(self)  # Track instance identity

    def query(self, sql: str) -> str:
        return f"PostgreSQL({self.host}:{self.port}): {sql}"


class FileLogger(Logger):
    """File logger implementation."""

    def __init__(self, filename: str = "app.log"):
        self.filename = filename
        self.messages = []
        self._instance_id = id(self)  # Track instance identity

    def log(self, message: str) -> None:
        self.messages.append(message)


class TestPerInjectorSingleton:
    """Test per-injector singleton behavior."""

    def test_singleton_returns_same_instance(self):
        """Test that SINGLETON returns the same instance within an injector."""

        class SingletonConfig(Config):
            def configure(self):
                self.register(
                    Database, PostgreSQL, singleton_type=SingletonType.SINGLETON
                )

        injector = get_injector(SingletonConfig)

        # First injection
        db1 = injector.inject(Database)
        assert isinstance(db1, PostgreSQL)

        # Second injection should return same instance
        db2 = injector.inject(Database)
        assert db2 is db1
        assert db2._instance_id == db1._instance_id

    def test_singleton_different_injectors_different_instances(self):
        """Test that different injectors get different singleton instances."""

        class SingletonConfig(Config):
            def configure(self):
                self.register(
                    Database, PostgreSQL, singleton_type=SingletonType.SINGLETON
                )

        injector1 = get_injector(SingletonConfig)
        injector2 = get_injector(SingletonConfig)

        db1 = injector1.inject(Database)
        db2 = injector2.inject(Database)

        # Should be different instances (per-injector singleton)
        assert db1 is not db2
        assert db1._instance_id != db2._instance_id

    def test_singleton_with_kwargs_uses_first_call(self):
        """Test that singleton uses kwargs from first call."""

        class SingletonConfig(Config):
            def configure(self):
                self.register(
                    Database, PostgreSQL, singleton_type=SingletonType.SINGLETON
                )

        injector = get_injector(SingletonConfig)

        # First call with specific kwargs
        db1 = injector.inject(Database, host="first", port=1111)
        assert db1.host == "first"
        assert db1.port == 1111

        # Second call with different kwargs - should return same instance
        db2 = injector.inject(Database, host="second", port=2222)
        assert db2 is db1
        assert db2.host == "first"  # Original kwargs preserved
        assert db2.port == 1111


class TestGlobalSingleton:
    """Test global singleton behavior."""

    def test_global_singleton_returns_same_instance(self):
        """Test that GLOBAL_SINGLETON returns the same instance across injectors."""
        # Clear any existing global singletons
        GlobalSingletonRegistry.clear()

        class GlobalSingletonConfig(Config):
            def configure(self):
                self.register(
                    Database, PostgreSQL, singleton_type=SingletonType.GLOBAL_SINGLETON
                )

        injector1 = get_injector(GlobalSingletonConfig)
        injector2 = get_injector(GlobalSingletonConfig)

        db1 = injector1.inject(Database)
        db2 = injector2.inject(Database)

        # Should be the same instance (global singleton)
        assert db1 is db2
        assert db1._instance_id == db2._instance_id

    def test_global_singleton_thread_safe(self):
        """Test that global singleton is thread-safe."""
        GlobalSingletonRegistry.clear()

        class GlobalSingletonConfig(Config):
            def configure(self):
                self.register(
                    Database, PostgreSQL, singleton_type=SingletonType.GLOBAL_SINGLETON
                )

        instances = []
        lock = threading.Lock()

        def get_instance():
            injector = get_injector(GlobalSingletonConfig)
            db = injector.inject(Database)
            with lock:
                instances.append(db)

        # Create multiple threads
        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same
        assert len(instances) == 10
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance
            assert instance._instance_id == first_instance._instance_id

    def test_global_singleton_persists_across_injectors(self):
        """Test that global singleton persists when creating new injectors."""
        GlobalSingletonRegistry.clear()

        class GlobalSingletonConfig(Config):
            def configure(self):
                self.register(
                    Database, PostgreSQL, singleton_type=SingletonType.GLOBAL_SINGLETON
                )

        # First injector
        injector1 = get_injector(GlobalSingletonConfig)
        db1 = injector1.inject(Database)

        # Second injector (new instance)
        injector2 = get_injector(GlobalSingletonConfig)
        db2 = injector2.inject(Database)

        # Should be same instance
        assert db1 is db2

        # Even after injector1 is gone, db2 should still work
        del injector1
        db3 = injector2.inject(Database)
        assert db3 is db2


class TestNoSingleton:
    """Test NONE singleton type (default behavior)."""

    def test_none_creates_new_instance_each_time(self):
        """Test that NONE creates a new instance each time."""

        class NoSingletonConfig(Config):
            def configure(self):
                self.register(Database, PostgreSQL, singleton_type=SingletonType.NONE)

        injector = get_injector(NoSingletonConfig)

        db1 = injector.inject(Database)
        db2 = injector.inject(Database)

        # Should be different instances
        assert db1 is not db2
        assert db1._instance_id != db2._instance_id


class TestSingletonBackwardCompatibility:
    """Test backward compatibility with singleton parameter."""

    def test_singleton_parameter_still_works(self):
        """Test that singleton=True still works (deprecated)."""

        class SingletonConfig(Config):
            def configure(self):
                self.register(Database, PostgreSQL, singleton=True)

        injector = get_injector(SingletonConfig)

        db1 = injector.inject(Database)
        db2 = injector.inject(Database)

        # Should return same instance
        assert db1 is db2

    def test_singleton_and_singleton_type_conflict(self):
        """Test that specifying both singleton and singleton_type raises error."""

        class ConflictConfig(Config):
            def configure(self):
                with pytest.raises(ValueError):
                    self.register(
                        Database,
                        PostgreSQL,
                        singleton=True,
                        singleton_type=SingletonType.GLOBAL_SINGLETON,
                    )


class TestGlobalSingletonRegistry:
    """Test GlobalSingletonRegistry directly."""

    def test_get_set_has(self):
        """Test basic registry operations."""
        GlobalSingletonRegistry.clear()

        class TestClass:
            pass

        # Initially should not exist
        assert not GlobalSingletonRegistry.has(TestClass)
        assert GlobalSingletonRegistry.get(TestClass) is None

        # Set an instance
        instance = TestClass()
        GlobalSingletonRegistry.set(TestClass, instance)

        # Should now exist
        assert GlobalSingletonRegistry.has(TestClass)
        assert GlobalSingletonRegistry.get(TestClass) is instance

    def test_clear(self):
        """Test clearing the registry."""
        GlobalSingletonRegistry.clear()

        class TestClass:
            pass

        instance = TestClass()
        GlobalSingletonRegistry.set(TestClass, instance)
        assert GlobalSingletonRegistry.has(TestClass)

        GlobalSingletonRegistry.clear()
        assert not GlobalSingletonRegistry.has(TestClass)
        assert GlobalSingletonRegistry.get(TestClass) is None
