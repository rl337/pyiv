"""Test factory functions that receive the injector as a parameter."""

import pytest
from abc import ABC, abstractmethod

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


class Service:
    """Service that depends on Database and Logger."""
    
    def __init__(self, db: Database, logger: Logger):
        self.db = db
        self.logger = logger


def test_factory_function_with_injector_parameter():
    """Test factory function that receives injector to resolve dependencies."""
    def create_service(injector: Injector) -> Service:
        """Factory function that uses injector to resolve dependencies."""
        db = injector.inject(Database)
        logger = injector.inject(Logger)
        return Service(db=db, logger=logger)
    
    class FactoryConfig(Config):
        def configure(self):
            self.register(Database, PostgreSQL)
            self.register(Logger, FileLogger)
            self.register(Service, create_service)
    
    injector = get_injector(FactoryConfig)
    service = injector.inject(Service)
    
    assert isinstance(service, Service)
    assert isinstance(service.db, PostgreSQL)
    assert isinstance(service.logger, FileLogger)
    
    # Verify it's the same instance if we inject again (if singleton)
    service2 = injector.inject(Service)
    # Service itself isn't registered as singleton, so should be different
    # But the dependencies should be the same if they're singletons

