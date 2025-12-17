"""pyiv - A lightweight dependency injection library for Python.

PyIV (Python Injection and Validation) is a lightweight, type-aware dependency
injection library designed for Python applications. It provides a simple yet
powerful way to manage dependencies, improve testability, and reduce coupling.

Key Features:
    - Type-based dependency resolution using annotations
    - Provider interface for lazy initialization and injector access
    - Scope management for extensible lifecycle control
    - Qualified bindings with type-safe keys
    - Fluent configuration API with Binder
    - Field/method injection with MembersInjector
    - Optional dependencies with Optional[T] support
    - Multibindings for multiple implementations
    - Singleton lifecycle management (per-injector or global)
    - Factory pattern support for complex object creation
    - Built-in abstractions for common dependencies (Clock, Filesystem, etc.)
    - Zero external dependencies (pure Python)

Architecture:
    The library is organized into modules:
    - config: Configuration base class for registering dependencies
    - injector: Core dependency injection engine
    - provider: Provider interface for lazy initialization
    - scope: Scope interface for lifecycle management
    - key: Key/Qualifier for type-safe qualified bindings
    - binder: Binder interface for fluent configuration
    - members: MembersInjector for field/method injection
    - optional: Optional dependency support
    - multibinder: Multibinder for multiple implementations
    - chain: Chain of responsibility pattern for extensible handlers
    - serde: Serialization/deserialization implementations
    - network: Network client abstractions (HTTP, HTTPS, etc.)
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

from pyiv.binder import Binder, BindingBuilder
from pyiv.chain import ChainHandler, ChainType
from pyiv.clock import Clock, RealClock, SyntheticClock, Timer
from pyiv.config import Config
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

__version__ = "0.2.15"
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
