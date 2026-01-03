# pyiv

A lightweight Python dependency injection framework with utility modules for filesystem operations, configuration management, and time/clock abstractions.

## Versioning

This project uses **automatic semantic versioning**:

- **Regular commits to main**: Automatically bumps patch version (0.1.0 → 0.1.1)
- **Merge commits to main**: Automatically bumps minor version (0.1.0 → 0.2.0)
- **Major versions**: Must be bumped manually using `poetry version major`

Version bumps happen automatically via GitHub Actions on every push to main. Both `pyproject.toml` and `pyiv/__init__.py` are updated automatically.

## Overview

pyiv (Python Injection) provides a simple yet powerful dependency injection system for Python applications, along with utility modules for common operations. It's designed to help manage dependencies, configuration, and cross-cutting concerns in Python projects.

## Features

- **Dependency Injection**: Clean dependency injection framework for Python applications
- **Provider Interface**: Lazy initialization and injector access for DI scenarios
- **Scope Management**: Extensible lifecycle management (singleton, request-scoped, custom scopes)
- **Qualified Bindings**: Type-safe keys and qualifiers for multiple implementations
- **Fluent Configuration**: Binder API for readable, chainable configuration
- **Field/Method Injection**: MembersInjector for framework integration and legacy code
- **Optional Dependencies**: Support for Optional[T] type hints with graceful degradation
- **Multibindings**: Multiple implementations of the same type (Set/List)
- **Reflection-Based Discovery**: Automatically discover interface implementations in packages
- **SerDe (Serialize/Deserialize)**: Unified interface for serialization with encoding type and name-based injection
- **Filesystem Utilities**: Enhanced filesystem operations and abstractions
- **Clock/Time Abstractions**: Time management utilities for testing and time-dependent code
- **Console Output**: File-like console interface for testable print() statements
- **DateTime Service**: Abstract datetime service for dependency injection and testing
- **Configuration Management**: Flexible configuration handling

## Installation

```bash
pip install pyiv
```

Or using Poetry:

```bash
poetry add pyiv
```

## Quick Start

### Dependency Injection

```python
from pyiv import Config, get_injector

# Define configuration
class MyConfig(Config):
    def configure(self):
        self.register(MyService, ConcreteService)
        self.register(MyRepository, ConcreteRepository)

# Create injector
injector = get_injector(MyConfig)

# Resolve dependencies
service = injector.inject(MyService)
```

### Reflection-Based Discovery

Instead of manually registering each implementation, you can use `ReflectionConfig` to automatically discover implementations in a package:

```python
from pyiv import ReflectionConfig, get_injector, SingletonType
from abc import ABC, abstractmethod

# Define interface
class Handler(ABC):
    @abstractmethod
    def handle(self, data: str) -> str:
        pass

# Define configuration with reflection
class MyConfig(ReflectionConfig):
    def configure(self):
        # Automatically discover all *Handler classes in my_service.handlers
        self.register_module(
            Handler,
            "my_service.handlers",
            pattern="*Handler",
            singleton_type=SingletonType.SINGLETON
        )

# Create injector
injector = get_injector(MyConfig)

# Get handler by name
handler_class = injector.inject_by_name(Handler, "CreateHandler")

# Get instance (respects singleton configuration)
handler = injector.inject(handler_class)
result = handler.handle("test")
```

### Filesystem Operations

```python
from pyiv.filesystem import FileSystem

fs = FileSystem()
content = fs.read_file('path/to/file.txt')
fs.write_file('path/to/output.txt', content)
```

### Clock/Time Management

```python
from pyiv.clock import Clock

clock = Clock()
current_time = clock.now()
```

### DateTime Service

```python
from pyiv.datetime_service import DateTimeService, PythonDateTimeService

# Production: use Python's datetime module
service = PythonDateTimeService()
utc_time = service.now_utc()
iso_string = service.now_utc_iso()

# Testing: use mock service with fixed time
from pyiv.datetime_service import MockDateTimeService
from datetime import datetime, timezone

mock_service = MockDateTimeService(datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc))
fixed_time = mock_service.now_utc()  # Returns the fixed time
```

### Console Output

Replace `print()` with injectable console for testable output:

```python
from pyiv import Config, get_injector
from pyiv.console import Console, RealConsole, MemoryConsole

class Service:
    def __init__(self, console: Console):
        self.console = console
    
    def greet(self, name: str):
        print(f"Hello, {name}!", file=self.console)

# Production: Use RealConsole (writes to stdout)
class MyConfig(Config):
    def configure(self):
        self.register(Console, RealConsole)

injector = get_injector(MyConfig)
service = injector.inject(Service)
service.greet("Alice")  # Prints to stdout

# Testing: Use MemoryConsole (captures output)
class TestConfig(Config):
    def configure(self):
        self.register(Console, MemoryConsole)

injector = get_injector(TestConfig)
service = injector.inject(Service)
service.greet("Bob")
assert "Hello, Bob!" in service.console.getvalue()
```

### SerDe (Serialize/Deserialize)

pyiv provides a unified SerDe interface for serialization/deserialization with support for multiple encoding types and implementations:

```python
from pyiv import Config, get_injector
from pyiv.serde import StandardJSONSerDe, GRPCJSONSerDe

# Register SerDe implementations
class MyConfig(Config):
    def configure(self):
        # Register by encoding type (default implementation)
        self.register_serde("json", StandardJSONSerDe)
        
        # Register by name (allows multiple implementations of same type)
        self.register_serde_by_name("json-grpc", GRPCJSONSerDe, "json")
        self.register_serde_by_name("json-input", CustomJSONSerDe, "json")
        self.register_serde_by_name("json-output", StandardJSONSerDe, "json")

# Create injector
injector = get_injector(MyConfig)

# Inject by encoding type
json_serde = injector.inject_serde("json")

# Inject by name (for specific implementations)
grpc_serde = injector.inject_serde_by_name("json-grpc")
input_serde = injector.inject_serde_by_name("json-input")
output_serde = injector.inject_serde_by_name("json-output")

# Use SerDe
data = {"key": "value", "number": 42}
serialized = json_serde.serialize(data)
deserialized = json_serde.deserialize(serialized)
```

#### Key Features

- **Encoding Type Selection**: Inject SerDe by encoding type (e.g., "json", "msgpack", "toml")
- **Named Instances**: Register and inject multiple implementations of the same encoding type
- **Custom Implementations**: Create custom SerDe implementations with different behaviors (e.g., date formatting, null handling)
- **Singleton Support**: SerDe instances respect singleton configuration
- **Type Safety**: Type-safe interface with abstract base class

#### Use Cases

1. **Multiple JSON Implementations**: Use different JSON SerDe instances for input/output with different date formatting
2. **gRPC Compatibility**: Use gRPC-compatible JSON serialization alongside standard JSON
3. **Encoding Translation**: Translate between different SerDe implementations (e.g., convert dates from one format to another)
4. **Multiple Encoding Types**: Support JSON, MessagePack, TOML, and other encoding types simultaneously

## Project Structure

```
pyiv/
├── pyiv/
│   ├── __init__.py
│   ├── injector.py      # Dependency injection framework
│   ├── config.py         # Configuration management
│   ├── provider.py       # Provider interface for lazy initialization
│   ├── scope.py          # Scope interface for lifecycle management
│   ├── key.py            # Key/Qualifier for qualified bindings
│   ├── binder.py         # Binder interface for fluent configuration
│   ├── binder_impl.py    # Binder implementation
│   ├── members.py        # MembersInjector for field/method injection
│   ├── optional.py       # Optional dependency support
│   ├── multibinder.py   # Multibinder for multiple implementations
│   ├── reflection.py     # Reflection-based discovery
│   ├── serde/            # SerDe (Serialize/Deserialize) module
│   │   ├── __init__.py
│   │   ├── base.py       # SerDe base interface
│   │   └── json.py       # JSON SerDe implementations
│   ├── filesystem.py     # Filesystem utilities
│   ├── clock.py          # Time/clock abstractions
│   ├── console.py        # Console output abstraction
│   ├── datetime_service.py  # DateTime service abstraction
│   └── singleton.py      # Singleton support
├── tests/                # Test suite
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

## Advanced Usage

### Provider Interface

Providers enable lazy initialization and injector access:

```python
from pyiv import Config, get_injector
from pyiv.provider import Provider, InjectorProvider

class Database:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

class Service:
    def __init__(self, db_provider: Provider[Database]):
        self._db_provider = db_provider
    
    def do_work(self):
        # Create database connection only when needed
        db = self._db_provider.get()
        return db.connection_string

class MyConfig(Config):
    def configure(self):
        self.register(Database, lambda: Database("postgresql://localhost/db"))
        self.register(Service, Service)

injector = get_injector(MyConfig)
service = injector.inject(Service)
service.do_work()  # Database created lazily
```

### Scope Management

Scopes control object lifecycle beyond simple singletons:

```python
from pyiv import Config, get_injector
from pyiv.scope import SingletonScope, GlobalSingletonScope

class MyConfig(Config):
    def configure(self):
        # Per-injector singleton
        self.register(Database, PostgreSQL, scope=SingletonScope())
        # Global singleton (shared across all injectors)
        self.register(Cache, RedisCache, scope=GlobalSingletonScope())
```

### Qualified Bindings with Keys

Use type-safe keys for multiple implementations:

```python
from pyiv import Config, get_injector
from pyiv.key import Key, Named

class MyConfig(Config):
    def configure(self):
        # Bind with qualifiers
        self.register_key(Key(Database, Named("primary")), PostgreSQL)
        self.register_key(Key(Database, Named("replica")), MySQL)

injector = get_injector(MyConfig)
primary_db = injector.inject(Key(Database, Named("primary")))
replica_db = injector.inject(Key(Database, Named("replica")))
```

### Fluent Configuration with Binder

Use the fluent Binder API for readable configuration:

```python
from pyiv import Config, get_injector
from pyiv.scope import SingletonScope

class MyConfig(Config):
    def configure(self):
        binder = self.get_binder()
        # Fluent API - easy to read and chain
        binder.bind(Database).to(PostgreSQL)
        binder.bind(Logger).to(FileLogger).in_scope(SingletonScope())
```

### Field Injection with MembersInjector

Inject dependencies into existing instances:

```python
from dataclasses import dataclass, field
from pyiv import Config, get_injector

@dataclass
class Service:
    db: Database = field(default=None)  # Will be injected

class MyConfig(Config):
    def configure(self):
        self.register(Database, PostgreSQL)

injector = get_injector(MyConfig)
service = Service()  # Created without dependencies
injector.inject_members(service)  # Inject dependencies
```

### Optional Dependencies

Use Optional[T] for graceful degradation:

```python
from typing import Optional
from pyiv import Config, get_injector

class Service:
    def __init__(self, db: Database, cache: Optional[Cache] = None):
        self.db = db
        self.cache = cache  # Will be None if Cache not registered

class MyConfig(Config):
    def configure(self):
        self.register(Database, PostgreSQL)
        # Cache is optional - will be None if not registered
```

### Multibindings

Register multiple implementations of the same type:

```python
from typing import Set, List
from pyiv import Config, get_injector

class MyConfig(Config):
    def configure(self):
        # Register multiple event handlers
        multibinder = self.multibinder(EventHandler, as_set=True)
        multibinder.add(EmailEventHandler)
        multibinder.add(SMSEventHandler)
        multibinder.add(PushEventHandler)

injector = get_injector(MyConfig)
# Inject all handlers as a Set
handlers = injector.inject(Set[EventHandler])
```

### Reflection-Based Discovery

`ReflectionConfig` allows you to automatically discover interface implementations in Python packages, eliminating the need for manual registration.

#### Key Features

- **Automatic Discovery**: Scans packages for classes implementing an interface
- **Pattern Matching**: Filter implementations by name pattern (e.g., `*Handler`)
- **Recursive Scanning**: Optionally scan submodules
- **Package Isolation**: Only discovers classes defined in the specified package (not imported from elsewhere)
- **Singleton Support**: Automatically registers discovered implementations with singleton configuration

#### Example

```python
from pyiv import ReflectionConfig, get_injector, SingletonType
from pyiv.filesystem import Filesystem

# Define a custom filesystem implementation
# my_service/filesystems.py
class CustomFilesystem(Filesystem):
    def open(self, file, mode="r", encoding=None):
        # Implementation...
        pass
    # ... other required methods

# Configure with reflection
class MyConfig(ReflectionConfig):
    def configure(self):
        # Discover all *Filesystem classes in my_service.filesystems
        self.register_module(
            Filesystem,
            "my_service.filesystems",
            pattern="*Filesystem",
            singleton_type=SingletonType.SINGLETON
        )

# Use it
injector = get_injector(MyConfig)
filesystem_class = injector.inject_by_name(Filesystem, "CustomFilesystem")
filesystem = injector.inject(filesystem_class)  # Singleton instance
```

#### Important Notes

- **Package Isolation**: Only classes **defined** in the registered package are discovered. Classes imported from other packages are excluded.
- **Interface Matching**: Classes must explicitly implement the interface (inherit from it).
- **Pattern Matching**: Uses `fnmatch` syntax (supports `*` wildcard).
- **Recursive Scanning**: When `recursive=True`, submodules are scanned. Submodule classes are named as `submodule.ClassName`.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black pyiv/ tests/

# Lint
pylint pyiv/

# Type checking
mypy pyiv/
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
