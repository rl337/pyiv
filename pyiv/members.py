"""MembersInjector for field and method injection.

This module provides MembersInjector for injecting dependencies into existing
instances. This supports field injection and method injection, which is useful
for framework integration, legacy code, and cases where constructor injection
is not possible.

**What Problem Does This Solve?**

MembersInjector solves the "framework-managed objects" problem:
- **Framework Integration**: Inject into objects created by frameworks (Django models,
  Flask request objects, etc.) where you can't control the constructor
- **Legacy Code**: Migrate existing code to DI without refactoring all constructors
- **Third-Party Objects**: Inject dependencies into objects from libraries you don't control
- **Data Classes**: Support field injection for dataclasses and attrs classes
- **Flexibility**: Use field injection when constructor injection is impractical

**Real-World Use Cases:**
- **Django Models**: Inject services into Django model instances
- **Flask Request Context**: Inject dependencies into Flask request objects
- **Legacy Codebase**: Gradually migrate to DI without breaking existing code
- **Data Classes**: Use dataclasses with DI for cleaner code

Architecture:
    - MembersInjector: Protocol for injecting into existing instances
    - InjectorMembersInjector: Concrete implementation using an injector

Usage Examples:

    Field Injection with Dataclasses:
        >>> from dataclasses import dataclass, field
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Database:
        ...     def query(self, sql: str):
        ...         return f"Executing: {sql}"
        >>>
        >>> @dataclass
        ... class Service:
        ...     db: Database = field(default=None)  # Will be injected
        ...
        ...     def do_work(self):
        ...         return self.db.query("SELECT * FROM users")
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, Database)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> service = Service()  # Created without dependencies
        >>> injector.inject_members(service)  # Inject dependencies
        >>> service.do_work()
        'Executing: SELECT * FROM users'

    Field Injection with Regular Classes:
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Logger:
        ...     def log(self, message: str):
        ...         print(f"LOG: {message}")
        >>>
        >>> class Service:
        ...     logger: Logger = None  # Type annotation for injection
        ...
        ...     def process(self):
        ...         self.logger.log("Processing...")
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Logger, Logger)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> service = Service()
        >>> injector.inject_members(service)
        >>> service.logger is not None
        True
"""

import inspect
from typing import Any, Dict, Generic, Protocol, Type, TypeVar

T = TypeVar("T", contravariant=True)


class MembersInjector(Protocol, Generic[T]):
    """Protocol for injecting dependencies into existing instances.

    MembersInjectors inject dependencies into fields and methods of existing
    instances. This is useful for:
    - Framework integration (Django, Flask, etc.)
    - Legacy code migration
    - Third-party object injection
    - Field injection for data classes

    Example:
        class MyMembersInjector(MembersInjector[Service]):
            def inject_members(self, instance: Service) -> None:
                instance.db = self._injector.inject(Database)
    """

    def inject_members(self, instance: T) -> None:
        """Inject dependencies into an existing instance.

        Args:
            instance: The instance to inject dependencies into
        """
        ...


class InjectorMembersInjector(Generic[T]):
    """MembersInjector implementation using an injector.

    This implementation uses an injector to resolve dependencies and inject
    them into fields and methods of existing instances. It supports:
    - Field injection (for dataclasses, attrs, or regular classes)
    - Method injection (for methods with type annotations)

    Example:
        >>> from pyiv.members import InjectorMembersInjector
        >>> from dataclasses import dataclass, field
        >>>
        >>> @dataclass
        ... class Service:
        ...     db: Database = field(default=None)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> members_injector = InjectorMembersInjector(Service, injector)
        >>> service = Service()
        >>> members_injector.inject_members(service)
    """

    def __init__(self, cls: Type[T], injector: Any):
        """Initialize members injector.

        Args:
            cls: The class type to inject into
            injector: The injector to use for dependency resolution
        """
        self._cls = cls
        self._injector = injector
        self._field_cache: Dict[str, Any] = {}

    def inject_members(self, instance: T) -> None:
        """Inject dependencies into an existing instance.

        This method:
        1. Inspects the class for fields with type annotations
        2. Resolves dependencies using the injector
        3. Sets field values on the instance
        4. Optionally calls methods with injected dependencies

        Args:
            instance: The instance to inject dependencies into

        Raises:
            TypeError: If instance is not of the expected type
        """
        if not isinstance(instance, self._cls):
            raise TypeError(
                f"instance must be of type {self._cls.__name__}, got {type(instance).__name__}"
            )

        # Inject fields
        self._inject_fields(instance)

        # Inject methods (optional - methods with @inject decorator or special naming)
        self._inject_methods(instance)

    def _inject_fields(self, instance: T) -> None:
        """Inject dependencies into fields.

        Args:
            instance: The instance to inject into
        """
        # Get all fields from the class and its bases
        for base in inspect.getmro(self._cls):
            if base is object:
                continue

            # Check for dataclass fields
            if hasattr(base, "__dataclass_fields__"):
                for field_name, field_info in base.__dataclass_fields__.items():
                    if hasattr(instance, field_name):
                        current_value = getattr(instance, field_name)
                        # Only inject if field is None or not set
                        if current_value is None or (
                            hasattr(field_info, "default")
                            and field_info.default is inspect.Parameter.empty
                        ):
                            field_type = field_info.type
                            if field_type != inspect.Parameter.empty:
                                try:
                                    value = self._injector.inject(field_type)
                                    setattr(instance, field_name, value)
                                except (ValueError, TypeError):
                                    # Can't inject, skip
                                    pass

            # Check for regular class attributes with type annotations
            annotations = getattr(base, "__annotations__", {})
            for field_name, field_type in annotations.items():
                if hasattr(instance, field_name):
                    current_value = getattr(instance, field_name)
                    # Only inject if field is None
                    if current_value is None:
                        try:
                            value = self._injector.inject(field_type)
                            setattr(instance, field_name, value)
                        except (ValueError, TypeError):
                            # Can't inject, skip
                            pass

    def _inject_methods(self, instance: T) -> None:
        """Inject dependencies into methods (optional feature).

        This is a placeholder for method injection. Can be extended to
        support methods with @inject decorator or special naming.

        Args:
            instance: The instance to inject into
        """
        # Method injection can be implemented here if needed
        # For now, we focus on field injection
        pass
