"""pyiv - A lightweight dependency injection library for Python.

PyIV (Python Injection and Validation) is a lightweight, type-aware dependency
injection library designed for Python applications. It provides a simple yet
powerful way to manage dependencies, improve testability, and reduce coupling.

Key Features:
    - Type-based dependency resolution using annotations
    - Singleton lifecycle management (per-injector or global)
    - Factory pattern support for complex object creation
    - Built-in abstractions for common dependencies (Clock, Filesystem, etc.)
    - Zero external dependencies (pure Python)

Architecture:
    The library is organized into modules:
    - config: Configuration base class for registering dependencies
    - injector: Core dependency injection engine
    - singleton: Singleton lifecycle management
    - factory: Factory pattern support
    - clock: Time abstraction for testing
    - filesystem: File I/O abstraction for testing
    - datetime_service: DateTime abstraction for testing

Quick Start:
    >>> from pyiv import Config, get_injector
    >>> class MyConfig(Config):
    ...     def configure(self):
    ...         self.register(Database, PostgreSQL)
    >>> injector = get_injector(MyConfig)
    >>> db = injector.inject(Database)

For more information, see the individual module documentation.
"""

from pyiv.clock import Clock, RealClock, SyntheticClock, Timer
from pyiv.config import Config
from pyiv.datetime_service import DateTimeService, MockDateTimeService, PythonDateTimeService
from pyiv.factory import BaseFactory, Factory, SimpleFactory
from pyiv.filesystem import Filesystem, MemoryFilesystem, RealFilesystem
from pyiv.injector import Injector, get_injector
from pyiv.reflection import ReflectionConfig
from pyiv.singleton import GlobalSingletonRegistry, SingletonType

# Command interface (optional import)
try:
    from pyiv.command import CLICommand, Command, CommandRunner, ServiceCommand

    _has_commands = True
except ImportError:
    _has_commands = False

__version__ = "0.2.12"
__all__ = [
    "Config",
    "ReflectionConfig",
    "Injector",
    "get_injector",
    "Filesystem",
    "RealFilesystem",
    "MemoryFilesystem",
    "Clock",
    "RealClock",
    "SyntheticClock",
    "Timer",
    "DateTimeService",
    "PythonDateTimeService",
    "MockDateTimeService",
    "Factory",
    "BaseFactory",
    "SimpleFactory",
    "SingletonType",
    "GlobalSingletonRegistry",
]

if _has_commands:
    __all__.extend(["Command", "ServiceCommand", "CLICommand", "CommandRunner"])
