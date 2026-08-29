"""Guice-style dependency injection for Python.

pyiv provides type-based constructor injection, scopes, qualified keys, and
built-in test doubles. Runtime has zero third-party dependencies. Python 3.8+.

Key Features:

- Type-based constructor injection from annotations
- Scopes (per-injector and process-wide singletons, plus custom Scope)
- Qualified keys and a fluent Binder API
- Reflection to discover implementations in a package
- Test doubles for Clock, Filesystem, Console, and DateTimeService
- Zero runtime dependencies

Quick Start:

    >>> from pyiv import Config, get_injector
    >>> class Database:
    ...     pass
    >>> class PostgreSQL(Database):
    ...     pass
    >>> class MyConfig(Config):
    ...     def configure(self):
    ...         self.register(Database, PostgreSQL)
    >>> injector = get_injector(MyConfig)
    >>> isinstance(injector.inject(Database), PostgreSQL)
    True
"""

from pyiv.binder import Binder, BindingBuilder
from pyiv.chain import ChainHandler, ChainType
from pyiv.clock import Clock, RealClock, SyntheticClock, Timer
from pyiv.config import Config
from pyiv.console import (
    BaseConsole,
    Console,
    FileConsole,
    MemoryConsole,
    MockConsole,
    PTYConsole,
    RealConsole,
)
from pyiv.datetime_service import DateTimeService, MockDateTimeService, PythonDateTimeService
from pyiv.factory import BaseFactory, Factory, SimpleFactory
from pyiv.filesystem import Filesystem, MemoryFilesystem, RealFilesystem
from pyiv.injector import Injector, get_injector
from pyiv.key import Key, Named, Qualifier
from pyiv.members import InjectorMembersInjector, MembersInjector
from pyiv.multibinder import ListMultibinder, Multibinder, SetMultibinder
from pyiv.network import HTTPClient, HTTPSClient, NetworkClient
from pyiv.optional import get_optional_type, is_optional_type
from pyiv.provider import (
    BaseProvider,
    FactoryProvider,
    InjectorProvider,
    InstanceProvider,
    Provider,
)
from pyiv.reflection import ReflectionConfig
from pyiv.scope import GlobalSingletonScope, NoScope, Scope, SingletonScope
from pyiv.serde import Base64SerDe, JSONSerDe, NoOpSerDe, PickleSerDe, SerDe, XMLSerDe, YAMLSerDe
from pyiv.singleton import GlobalSingletonRegistry, SingletonType

# Command interface (optional import)
try:
    from pyiv.command import CLICommand, Command, CommandRunner, ServiceCommand

    _has_commands = True
except ImportError:
    _has_commands = False

__version__ = "0.2.24"
__all__ = [
    "Config",
    "ReflectionConfig",
    "Injector",
    "get_injector",
    "ChainType",
    "ChainHandler",
    "Filesystem",
    "RealFilesystem",
    "MemoryFilesystem",
    "Console",
    "BaseConsole",
    "RealConsole",
    "MemoryConsole",
    "FileConsole",
    "PTYConsole",
    "MockConsole",
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
    "SerDe",
    "JSONSerDe",
    "Base64SerDe",
    "XMLSerDe",
    "YAMLSerDe",
    "PickleSerDe",
    "NoOpSerDe",
    "NetworkClient",
    "HTTPClient",
    "HTTPSClient",
    "SingletonType",
    "GlobalSingletonRegistry",
    # New interfaces
    "Provider",
    "BaseProvider",
    "InjectorProvider",
    "InstanceProvider",
    "FactoryProvider",
    "Scope",
    "NoScope",
    "SingletonScope",
    "GlobalSingletonScope",
    "Key",
    "Named",
    "Qualifier",
    "Binder",
    "BindingBuilder",
    "MembersInjector",
    "InjectorMembersInjector",
    "Multibinder",
    "SetMultibinder",
    "ListMultibinder",
    "is_optional_type",
    "get_optional_type",
]

if _has_commands:
    __all__.extend(["Command", "ServiceCommand", "CLICommand", "CommandRunner"])
