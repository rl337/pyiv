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
- **Reflection-Based Discovery**: Automatically discover interface implementations in packages
- **SerDe (Serialize/Deserialize)**: Unified interface for serialization with encoding type and name-based injection
- **Filesystem Utilities**: Enhanced filesystem operations and abstractions
- **Clock/Time Abstractions**: Time management utilities for testing and time-dependent code
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
│   ├── reflection.py     # Reflection-based discovery
│   ├── serde/            # SerDe (Serialize/Deserialize) module
│   │   ├── __init__.py
│   │   ├── base.py       # SerDe base interface
│   │   └── json.py       # JSON SerDe implementations
│   ├── filesystem.py     # Filesystem utilities
│   ├── clock.py          # Time/clock abstractions
│   ├── datetime_service.py  # DateTime service abstraction
│   └── singleton.py      # Singleton support
├── tests/                # Test suite
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

## Advanced Usage

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
