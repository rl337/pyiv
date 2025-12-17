# Guice Comparison: Base Interfaces for pyiv

This document compares pyiv to Google Guice and identifies base interfaces that should be added to cover similar functionality without adding external dependencies.

## Current pyiv Architecture

### What pyiv has (similar to Guice):
- **Config** → Similar to Guice's `Module`
- **Injector** → Same concept as Guice's `Injector`
- **Factory/BaseFactory** → Similar to `Provider<T>` but different focus
- **SingletonType** → Lifecycle management (enum-based)
- **ChainHandler** → Extensible handler pattern
- **ReflectionConfig** → Automatic discovery

## Missing Base Interfaces (from Guice)

### 1. **Provider<T>** (High Priority)
**Guice Equivalent:** `com.google.inject.Provider<T>`

**Purpose:** DI-focused interface for providing instances. More specialized than Factory for dependency injection scenarios.

**Why it's different from Factory:**
- Factory is for general object creation
- Provider is specifically for DI scenarios where you need access to the injector
- Provider instances can be injected themselves
- Standard pattern in DI frameworks

**Interface:**
```python
class Provider(Protocol, Generic[T]):
    def get(self) -> T:
        """Get an instance of type T."""
        ...
```

**Use Cases:**
- Lazy initialization with injector access
- Creating instances that need the injector
- Deferred creation until needed
- Multiple instances of the same type

**Implementation Notes:**
- Can wrap existing Factory implementations
- Should integrate with Injector for dependency resolution
- Can be registered in Config like other dependencies

---

### 2. **Scope** (High Priority)
**Guice Equivalent:** `com.google.inject.Scope`

**Purpose:** Extensible lifecycle management beyond the SingletonType enum.

**Why it's better than SingletonType enum:**
- Allows custom scopes (e.g., RequestScope, SessionScope, ThreadScope)
- More extensible architecture
- Can be composed and chained
- Follows open/closed principle

**Interface:**
```python
class Scope(Protocol):
    def scope(self, key: Type, provider: Provider) -> Provider:
        """Scope a provider to this scope's lifecycle."""
        ...
```

**Use Cases:**
- Request-scoped dependencies (web frameworks)
- Thread-local scopes
- Session scopes
- Custom application-specific scopes

**Implementation Notes:**
- SingletonType can be refactored to use Scope internally
- Default scopes: NoScope, SingletonScope, GlobalSingletonScope
- Can be registered per binding in Config

---

### 3. **Key/Qualifier** (Medium Priority)
**Guice Equivalent:** `com.google.inject.Key`, `@Named`, `@Qualifier`

**Purpose:** Type-safe qualified bindings for multiple implementations of the same type.

**Why it's useful:**
- Type-safe alternative to string-based names
- Better IDE support
- Compile-time checking
- More Pythonic than string qualifiers

**Interface:**
```python
class Key(Generic[T]):
    """Type-safe key for qualified bindings."""
    type: Type[T]
    annotation: Optional[Any] = None  # For @Named or custom qualifiers
    name: Optional[str] = None
```

**Use Cases:**
- Multiple database connections
- Different logger implementations
- Input vs output serializers
- Environment-specific configurations

**Implementation Notes:**
- Can use typing annotations or custom qualifier classes
- Integrates with existing named binding system
- Should support both string names and type annotations

---

### 4. **Binder** (Medium Priority)
**Guice Equivalent:** `com.google.inject.Binder`

**Purpose:** Fluent API for configuration, decoupled from Config class.

**Why it's useful:**
- Separates configuration API from implementation
- Enables fluent method chaining
- Makes Config more testable
- Allows programmatic configuration

**Interface:**
```python
class Binder(Protocol):
    def bind(self, abstract: Type) -> BindingBuilder:
        """Start a binding configuration."""
        ...
    
    def bind_instance(self, abstract: Type, instance: Any) -> None:
        """Bind to a pre-created instance."""
        ...
    
    def install(self, module: Config) -> None:
        """Install another configuration module."""
        ...
```

**Use Cases:**
- Fluent configuration API
- Programmatic configuration
- Testing with mock binders
- Modular configuration composition

**Implementation Notes:**
- Config can use Binder internally
- Backward compatible with existing Config API
- Enables more advanced configuration patterns

---

### 5. **MembersInjector** (Low Priority)
**Guice Equivalent:** `com.google.inject.MembersInjector<T>`

**Purpose:** Inject dependencies into existing instances (field/method injection).

**Why it's useful:**
- Framework integration (e.g., Django, Flask)
- Legacy code migration
- Third-party object injection
- Field injection support

**Interface:**
```python
class MembersInjector(Protocol, Generic[T]):
    def inject_members(self, instance: T) -> None:
        """Inject dependencies into an existing instance."""
        ...
```

**Use Cases:**
- Injecting into framework-managed objects
- Legacy code that can't use constructor injection
- Field injection for data classes
- Method injection for lifecycle hooks

**Implementation Notes:**
- Requires type annotations on fields/methods
- Can use dataclasses or attrs
- Should support both field and method injection
- Lower priority since constructor injection is preferred

---

### 6. **OptionalBinder** (Low Priority)
**Guice Equivalent:** `com.google.inject.multibindings.OptionalBinder`

**Purpose:** Support for `Optional[T]` type hints with default values.

**Why it's useful:**
- Type-safe optional dependencies
- Better than None checks
- Clearer intent in code
- Better type checking

**Use Cases:**
- Optional plugins
- Feature flags
- Environment-specific dependencies
- Graceful degradation

**Implementation Notes:**
- Can be handled in dependency resolution
- Should detect Optional[T] in type annotations
- Provide default if not registered
- Integrate with existing injector logic

---

### 7. **Multibinder** (Low Priority)
**Guice Equivalent:** `com.google.inject.multibindings.Multibinder`

**Purpose:** Bind multiple implementations of the same type.

**Why it's useful:**
- Plugin systems
- Chain of responsibility
- Strategy pattern with multiple strategies
- Event handlers

**Use Cases:**
- Multiple event listeners
- Plugin registrations
- Chain handlers (we have this via ChainHandler)
- Multiple validators

**Implementation Notes:**
- Similar to ChainHandler but more general
- Can inject List[T] or Set[T]
- Should respect order for List
- May overlap with existing ChainHandler pattern

---

## Recommended Implementation Order

### Phase 1: Core DI Interfaces
1. **Provider<T>** - Essential for DI patterns
2. **Scope** - Extensible lifecycle management

### Phase 2: Enhanced Configuration
3. **Key/Qualifier** - Type-safe qualified bindings
4. **Binder** - Fluent configuration API

### Phase 3: Advanced Features (if needed)
5. **MembersInjector** - Field/method injection
6. **OptionalBinder** - Optional dependency support
7. **Multibinder** - Multiple implementations

## Design Principles

1. **Zero Dependencies:** All interfaces use only Python stdlib
2. **Backward Compatible:** New interfaces don't break existing code
3. **Protocol-Based:** Use `typing.Protocol` for interfaces (Pythonic)
4. **Type-Safe:** Leverage Python's type system fully
5. **Extensible:** Allow custom implementations

## Notes

- **Factory vs Provider:** Keep both - Factory for general object creation, Provider for DI-specific scenarios
- **SingletonType vs Scope:** Scope is more powerful, but SingletonType can remain as a convenience
- **ChainHandler vs Multibinder:** ChainHandler is more specialized, Multibinder is more general - both have value
- **Config vs Binder:** Config can use Binder internally, providing both APIs

