"""Guice-style dependency injection for Python.

pyiv provides type-based constructor injection, scopes, qualified keys, and
built-in test doubles. Runtime has zero third-party dependencies. Python 3.8+.

Key Features:

- Type-based constructor injection from annotations
- Scopes (per-injector and process-wide singletons, plus custom Scope)
- Qualified keys with tag sets (``Named``), nearest match (``Matched``),
  ``Annotated`` constructor injection, and Binder
- Module install, private modules, child injectors, and config override
- Map/Set/List multibinders; Stage.PRODUCTION eager singletons
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

    Multiple Implementations With Tags:

    >>> from pyiv import Config, get_injector, Key, Named, Matched
    >>> class Encoder:
    ...     def __init__(self, kind: str = ""):
    ...         self.kind = kind
    >>> class JSONEncoder(Encoder):
    ...     def __init__(self):
    ...         super().__init__("json")
    >>> class PrettyJSONEncoder(Encoder):
    ...     def __init__(self):
    ...         super().__init__("pretty")
    >>> class EncoderConfig(Config):
    ...     def configure(self):
    ...         self.register_key(Key(Encoder, Named("json")), JSONEncoder)
    ...         self.register_key(
    ...             Key(Encoder, Named(["json", "pretty"], default=True)),
    ...             PrettyJSONEncoder,
    ...         )
    >>> inj = get_injector(EncoderConfig)
    >>> inj.inject(Key(Encoder, Matched(required=["json"], prefer=["pretty"]))).kind
    'pretty'
    >>> inj.inject(Encoder).kind
    'pretty'

    Constructor Annotated (see the keys guide for limits — not on fields):

    >>> from typing import Annotated
    >>> from pyiv import Config, get_injector, Key, Named
    >>> class Host:
    ...     def __init__(self, enc: Annotated[Encoder, Named("json")]):
    ...         self.enc = enc
    >>> class HostConfig(Config):
    ...     def configure(self):
    ...         self.register_key(Key(Encoder, Named("json")), JSONEncoder)
    >>> get_injector(HostConfig).inject(Host).enc.kind
    'json'
"""

from pyiv.binder import Binder, BindingBuilder
from pyiv.chain import ChainHandler, ChainType
from pyiv.clock import Clock, RealClock, SyntheticClock, Timer
from pyiv.config import Config, PrivateConfig
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
from pyiv.errors import CreationError
from pyiv.factory import BaseFactory, Factory, SimpleFactory
from pyiv.filesystem import Filesystem, MemoryFilesystem, RealFilesystem
from pyiv.injector import Injector, get_injector
from pyiv.key import Key, Matched, Named, Qualifier
from pyiv.members import InjectorMembersInjector, MembersInjector
from pyiv.multibinder import ListMultibinder, MapMultibinder, Multibinder, SetMultibinder
from pyiv.network import HTTPClient, HTTPSClient, NetworkClient
from pyiv.optional import get_optional_type, is_optional_type
from pyiv.override import override
from pyiv.provider import (
    BaseProvider,
    FactoryProvider,
    InjectorProvider,
    InstanceProvider,
    Provider,
)
from pyiv.reflection import ReflectionConfig
from pyiv.scope import GlobalSingletonScope, NoScope, Scope, SingletonScope
from pyiv.serde import Base64SerDe, JSONSerDe, NoOpSerDe, PickleSerDe, SerDe, XMLSerDe
from pyiv.singleton import GlobalSingletonRegistry, SingletonType
from pyiv.stage import Stage

# Command interface (optional import)
try:
    from pyiv.command import CLICommand, Command, CommandRunner, ServiceCommand

    _has_commands = True
except ImportError:
    _has_commands = False

__version__ = "0.4.1"
__all__ = [
    "Config",
    "PrivateConfig",
    "ReflectionConfig",
    "Injector",
    "get_injector",
    "Stage",
    "CreationError",
    "override",
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
    "PickleSerDe",
    "NoOpSerDe",
    "NetworkClient",
    "HTTPClient",
    "HTTPSClient",
    "SingletonType",
    "GlobalSingletonRegistry",
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
    "Matched",
    "Qualifier",
    "Binder",
    "BindingBuilder",
    "MembersInjector",
    "InjectorMembersInjector",
    "Multibinder",
    "SetMultibinder",
    "ListMultibinder",
    "MapMultibinder",
    "is_optional_type",
    "get_optional_type",
]

if _has_commands:
    __all__.extend(["Command", "ServiceCommand", "CLICommand", "CommandRunner"])
