# Agent Guidelines for pyiv

This document provides guidelines for AI agents working on the pyiv project.

## Project Overview

pyiv is a lightweight dependency injection library for Python. It provides a simple, flexible way to manage dependencies and supports features like singletons, factories, and reflection-based discovery.

## Versioning

**IMPORTANT**: This project uses **automatic semantic versioning** via GitHub Actions.

### How It Works

- **Regular commits to main**: Automatically bumps patch version (0.1.0 → 0.1.1)
- **Merge commits to main**: Automatically bumps minor version (0.1.0 → 0.2.0)
- **Major versions**: Must be bumped manually using `poetry version major`

### What This Means for Agents

1. **Do NOT manually update versions** in `pyproject.toml` or `pyiv/__init__.py` unless:
   - You're bumping a major version (breaking changes)
   - You're fixing a version that got out of sync

2. **Version bumps are automatic**: When you commit to main (or merge a PR), the version will be automatically bumped by the GitHub Actions workflow.

3. **Version sync**: The workflow updates both:
   - `pyproject.toml` (the `version = "X.Y.Z"` field)
   - `pyiv/__init__.py` (the `__version__ = "X.Y.Z"` field)

4. **Skip CI**: Version bump commits include `[skip ci]` to prevent infinite loops.

### Manual Version Bumping

If you need to manually bump a major version:

```bash
poetry version major
# Then manually update pyiv/__init__.py to match
```

## Development Workflow

1. Create feature branches from `main`
2. Make changes and commit
3. Open PR to `main`
4. When merged, version is automatically bumped:
   - PR merge → minor version bump
   - Direct commit → patch version bump

## Testing

- Run tests: `poetry run pytest`
- Run with coverage: `poetry run pytest --cov=pyiv`
- All tests must pass before merging

## Code Style

- Use `black` for formatting (line length 100)
- Use `isort` for import sorting (profile: black)
- Use `mypy` for type checking
- Run `./run_checks.sh` to verify all checks pass

## Build Artifacts

**IMPORTANT**: All build artifacts should be placed in a `build/` directory that is in `.gitignore`.

### Build Directory Structure

All projects should have a `build/` directory (separate from Python's `build/` for distribution) where build artifacts are stored:

- **Security reports**: `build/bandit-report.json`
- **Coverage reports**: `build/coverage.xml`, `build/htmlcov/` (if needed)
- **Test reports**: `build/test-results.xml`
- **Any other generated files**: All build outputs go in `build/`

### Why This Matters

- Keeps the repository clean
- Prevents accidentally committing generated files
- Makes it clear what files are build artifacts vs source code
- Allows easy cleanup with `rm -rf build/`

### Implementation

1. Add `build/` to `.gitignore` (if not already present)
2. Update scripts to output to `build/` directory
3. Create `build/` directory structure as needed
4. Never commit files from `build/` directory

Example:
```bash
# Create build directory if it doesn't exist
mkdir -p build

# Output artifacts to build/
bandit -r pyiv/ -f json -o build/bandit-report.json
pytest --cov-report=xml --cov-report=term-missing --cov-report=html:build/htmlcov
```

## Documentation Standards

**IMPORTANT**: All modules and interfaces must follow these documentation standards.

### Module Documentation Requirements

Every module must include:

1. **Module-Level Docstring** with:
   - Clear description of what the module provides
   - **"What Problem Does This Solve?"** section explaining the real-world problems
   - **"Real-World Use Cases"** section with concrete examples
   - Architecture overview
   - Usage examples with doctest-compatible code

2. **Interface/Class Documentation** with:
   - Clear description of the interface/class
   - **Doctest examples** that demonstrate usage
   - Examples should be runnable and testable

3. **Method Documentation** with:
   - Clear parameter descriptions
   - Return value descriptions
   - Doctest examples where appropriate

### Documentation Format

```python
"""Module title and brief description.

This module provides [what it provides] for [what purpose].

**What Problem Does This Solve?**

[Clear explanation of the problems this solves, why it exists]

**Real-World Use Cases:**
- [Use case 1]
- [Use case 2]
- [Use case 3]

Architecture:
    - Component1: Description
    - Component2: Description

Usage Examples:

    Basic Usage:
        >>> from pyiv.module import Component
        >>> # Example code that works
        >>> result = Component()
        >>> result.value
        'expected'

    Advanced Usage:
        >>> # More complex example
        >>> # ...
"""
```

### Doctest Requirements

1. **All examples must be runnable**: Use `>>>` prompt and ensure code actually works
2. **Test all examples**: Run `python -m doctest pyiv/module.py` to verify
3. **Use realistic examples**: Show actual use cases, not contrived examples
4. **Include assertions**: Show expected results with assertions or comparisons

### Anecdotes and Problem Statements

Every interface/module must explain:
- **What problem it solves**: Why does this exist? What gap does it fill?
- **When to use it**: What scenarios call for this interface?
- **Real-world examples**: Concrete use cases from actual applications

### Example Template

```python
class MyInterface:
    """Interface description.

    **What Problem Does This Solve?**
    
    This interface solves [specific problem]. It addresses [pain points]
    by providing [solution approach].

    **Real-World Use Cases:**
    - [Specific scenario 1]
    - [Specific scenario 2]

    Example:
        >>> from pyiv.module import MyInterface
        >>> 
        >>> class Implementation(MyInterface):
        ...     def method(self):
        ...         return "result"
        >>> 
        >>> impl = Implementation()
        >>> impl.method()
        'result'
    """
```

### Verification

Before committing:
1. Run doctests: `python -m doctest pyiv/module.py -v`
2. Verify examples work: Actually run the code in examples
3. Check for typos and clarity
4. Ensure all public interfaces have examples

### Why These Standards Matter

- **Discoverability**: Developers can understand what each interface does
- **Testability**: Doctests serve as both documentation and tests
- **Maintainability**: Clear problem statements help future maintainers
- **Onboarding**: New developers can quickly understand the codebase

## Design Principles

When implementing new features, follow these principles:

1. **Zero Dependencies:** All interfaces use only Python stdlib
2. **Backward Compatible:** New interfaces don't break existing code
3. **Protocol-Based:** Use `typing.Protocol` for interfaces (Pythonic)
4. **Type-Safe:** Leverage Python's type system fully
5. **Extensible:** Allow custom implementations

## Interface Design Guidelines

### Factory vs Provider
- **Factory**: For general object creation, not DI-specific
- **Provider**: For DI scenarios where you need injector access or lazy initialization
- Keep both - they serve different purposes

### SingletonType vs Scope
- **SingletonType**: Enum-based, simple and convenient (backward compatible)
- **Scope**: More powerful, extensible, supports custom scopes
- Scope is the future, but SingletonType remains for compatibility

### ChainHandler vs Multibinder
- **ChainHandler**: Specialized for chain of responsibility patterns
- **Multibinder**: General-purpose multiple implementations
- Both have value - use ChainHandler for chains, Multibinder for general collections

### Config vs Binder
- **Config**: Direct registration API (simpler, more Pythonic)
- **Binder**: Fluent API (more readable, better for complex configurations)
- Config uses Binder internally - both APIs are available

## Key Files

- `pyproject.toml`: Project configuration and dependencies
- `pyiv/__init__.py`: Package exports and version
- `.github/workflows/version-bump.yml`: Automatic version bumping workflow
- `.github/workflows/ci.yml`: CI/CD pipeline

