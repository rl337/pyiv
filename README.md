# pyiv

A lightweight Python dependency injection framework with utility modules for filesystem operations, configuration management, and time/clock abstractions.

## Overview

pyiv (Python Injection) provides a simple yet powerful dependency injection system for Python applications, along with utility modules for common operations. It's designed to help manage dependencies, configuration, and cross-cutting concerns in Python projects.

## Features

- **Dependency Injection**: Clean dependency injection framework for Python applications
- **Filesystem Utilities**: Enhanced filesystem operations and abstractions
- **Clock/Time Abstractions**: Time management utilities for testing and time-dependent code
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
from pyiv import Injector

# Create an injector
injector = Injector()

# Register dependencies
injector.register(MyService)
injector.register(MyRepository)

# Resolve dependencies
service = injector.resolve(MyService)
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

## Project Structure

```
pyiv/
├── pyiv/
│   ├── __init__.py
│   ├── injector.py      # Dependency injection framework
│   ├── filesystem.py     # Filesystem utilities
│   ├── clock.py          # Time/clock abstractions
│   └── config.py          # Configuration management
├── tests/                # Test suite
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

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
