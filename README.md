# pyiv

A lightweight dependency injection library for Python with built-in abstractions for common operations.

## Installation

```bash
pip install pyiv
```

## Quick Start

### Basic Dependency Injection

```python
import pyiv
from abc import ABC, abstractmethod

# Define abstract interfaces
class Database(ABC):
    @abstractmethod
    def query(self, sql: str):
        pass

class Logger(ABC):
    @abstractmethod
    def log(self, message: str):
        pass

# Define concrete implementations
class PostgreSQL(Database):
    def query(self, sql: str):
        return f"PostgreSQL: {sql}"

class FileLogger(Logger):
    def log(self, message: str):
        print(f"LOG: {message}")

# Create configuration
class AppConfig(pyiv.Config):
    def configure(self):
        self.register(Database, PostgreSQL)
        self.register(Logger, FileLogger)

# Get injector and use it
injector = pyiv.get_injector(AppConfig)

# Inject dependencies
db = injector.inject(Database)
logger = injector.inject(Logger)

# Or inject with additional kwargs
db = injector.inject(Database, host="localhost", port=5432)
```

### Filesystem Abstraction

Replace file operation patching with dependency injection:

```python
import pyiv

class AppConfig(pyiv.Config):
    def configure(self):
        # Production: use real filesystem
        self.register(pyiv.Filesystem, pyiv.RealFilesystem)
        
        # Or for testing: use in-memory filesystem
        # self.register(pyiv.Filesystem, pyiv.MemoryFilesystem)

injector = pyiv.get_injector(AppConfig)
fs = injector.inject(pyiv.Filesystem)

# Use filesystem abstraction
fs.write_text("/path/to/file.txt", "content")
content = fs.read_text("/path/to/file.txt")
```

### Clock Abstraction

Replace time operation patching with dependency injection:

```python
import pyiv

class AppConfig(pyiv.Config):
    def configure(self):
        # Production: use real clock
        self.register(pyiv.Clock, pyiv.RealClock)
        
        # Or for testing: use synthetic clock
        # clock = pyiv.SyntheticClock(start_time=0.0)
        # self.register_instance(pyiv.Clock, clock)

injector = pyiv.get_injector(AppConfig)
clock = injector.inject(pyiv.Clock)

# Use clock abstraction
current_time = clock.time()
clock.sleep(1.0)  # In tests, this advances synthetic time instead of sleeping

# For testing with synthetic clock
test_clock = pyiv.SyntheticClock(start_time=0.0)
test_clock.advance(5.0)  # Manually advance time
assert test_clock.time() == 5.0
```

## Features

- **Dependency Injection**: Clean dependency injection without patching
- **Filesystem Abstraction**: Replace `open()`, `Path`, etc. with injectable filesystem
- **Clock Abstraction**: Replace `time.sleep()`, `time.time()`, etc. with injectable clock
- **Singleton Support**: Register singletons for shared instances
- **Automatic Dependency Resolution**: Dependencies resolved from type hints

## License

MIT

