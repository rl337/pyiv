"""Tests for the Injector class."""

from abc import ABC, abstractmethod

import pytest

import pyiv
from pyiv import Config, Injector, get_injector


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

    def query(self, sql: str) -> str:
        return f"PostgreSQL({self.host}:{self.port}): {sql}"


class FileLogger(Logger):
    """File logger implementation."""

    def __init__(self, filename: str = "app.log"):
        self.filename = filename
        self.messages = []

    def log(self, message: str) -> None:
        self.messages.append(message)


class AppTestConfig(Config):
    """Test configuration."""

    def configure(self):
        self.register(Database, PostgreSQL)
        self.register(Logger, FileLogger)


def test_get_injector():
    """Test creating an injector from a config class."""
    injector = get_injector(AppTestConfig)
    assert isinstance(injector, Injector)


def test_inject_registered_class():
    """Test injecting a registered abstract class."""
    injector = get_injector(AppTestConfig)
    db = injector.inject(Database)

    assert isinstance(db, PostgreSQL)
    assert db.host == "localhost"
    assert db.port == 5432


def test_inject_with_kwargs():
    """Test injecting with additional keyword arguments."""
    injector = get_injector(AppTestConfig)
    db = injector.inject(Database, host="remote", port=3306)

    assert isinstance(db, PostgreSQL)
    assert db.host == "remote"
    assert db.port == 3306


def test_inject_singleton():
    """Test singleton registration."""

    class SingletonConfig(Config):
        def configure(self):
            self.register(Database, PostgreSQL, singleton=True)

    injector = get_injector(SingletonConfig)
    db1 = injector.inject(Database)
    db2 = injector.inject(Database)

    assert db1 is db2  # Same instance


def test_inject_instance():
    """Test injecting a registered instance."""
    logger_instance = FileLogger("test.log")

    class InstanceConfig(Config):
        def configure(self):
            self.register_instance(Logger, logger_instance)

    injector = get_injector(InstanceConfig)
    logger = injector.inject(Logger)

    assert logger is logger_instance


def test_inject_unregistered_concrete():
    """Test injecting a concrete class that isn't registered."""
    injector = get_injector(AppTestConfig)
    # Should be able to inject concrete classes directly
    db = injector.inject(PostgreSQL, host="test")

    assert isinstance(db, PostgreSQL)
    assert db.host == "test"


def test_dependency_injection():
    """Test automatic dependency injection from type hints."""

    class Service:
        def __init__(self, db: Database, logger: Logger):
            self.db = db
            self.logger = logger

    injector = get_injector(AppTestConfig)
    service = injector.inject(Service)

    assert isinstance(service.db, PostgreSQL)
    assert isinstance(service.logger, FileLogger)


def test_factory_function():
    """Test using a factory function for registration."""

    def create_database() -> Database:
        return PostgreSQL(host="factory", port=9999)

    class FactoryConfig(Config):
        def configure(self):
            self.register(Database, create_database)

    injector = get_injector(FactoryConfig)
    db = injector.inject(Database)

    assert isinstance(db, PostgreSQL)
    assert db.host == "factory"
    assert db.port == 9999


def test_get_injector_with_config_instance():
    """Test get_injector with a Config instance."""

    class TestConfig(Config):
        def __init__(self, value: str):
            self.value = value
            super().__init__()

        def configure(self):
            self.register_instance(str, self.value)

    # Create instance with parameter
    config_instance = TestConfig("test-value")
    injector = get_injector(config_instance)

    # Should use the instance directly
    value = injector.inject(str)
    assert value == "test-value"


def test_get_injector_with_config_class():
    """Test get_injector with a Config class (original behavior)."""

    class TestConfig(Config):
        def configure(self):
            self.register_instance(str, "default-value")

    injector = get_injector(TestConfig)
    value = injector.inject(str)
    assert value == "default-value"


def test_get_injector_invalid_type():
    """Test get_injector with invalid type."""
    with pytest.raises(TypeError):
        get_injector("not-a-config")
