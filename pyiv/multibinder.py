"""Multibinder for binding multiple implementations of the same type.

This module provides Multibinder for registering and injecting multiple
implementations of the same type. This is useful for plugin systems,
event handlers, chain of responsibility patterns, and strategy patterns
with multiple strategies.

**What Problem Does This Solve?**

Multibinders solve the "multiple implementations" problem:
- **Plugin Systems**: Register and inject multiple plugins of the same type
- **Event Handlers**: Multiple event handlers that all need to be notified
- **Chain of Responsibility**: Multiple handlers that process requests in sequence
- **Strategy Pattern**: Multiple strategies that can be applied
- **Validation Chains**: Multiple validators that all need to run

**Real-World Use Cases:**
- **Event System**: Multiple event listeners for the same event type
- **Validation Pipeline**: Multiple validators that all need to run
- **Middleware Stack**: Multiple middleware components in a web framework
- **Plugin Architecture**: Multiple plugins that extend functionality

Architecture:
    - Multibinder: Interface for binding multiple implementations
    - SetMultibinder: Binds to a Set[T] (no duplicates, no order)
    - ListMultibinder: Binds to a List[T] (preserves order, allows duplicates)

Usage Examples:

    Using SetMultibinder (No Order, No Duplicates):
        >>> from typing import Set
        >>> from pyiv import Config, get_injector
        >>>
        >>> class EventHandler:
        ...     def handle(self, event: str):
        ...         pass
        >>>
        >>> class EmailHandler(EventHandler):
        ...     def handle(self, event: str):
        ...         return f"Email: {event}"
        >>>
        >>> class SMSHandler(EventHandler):
        ...     def handle(self, event: str):
        ...         return f"SMS: {event}"
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         multibinder = self.multibinder(EventHandler, as_set=True)
        ...         multibinder.add(EmailHandler)
        ...         multibinder.add(SMSHandler)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> handlers = injector.inject(Set[EventHandler])
        >>> len(handlers)
        2
        >>> # All handlers are available
        >>> handler_types = {type(h).__name__ for h in handlers}
        >>> 'EmailHandler' in handler_types
        True
        >>> 'SMSHandler' in handler_types
        True

    Using ListMultibinder (Preserves Order):
        >>> from typing import List
        >>>
        >>> class Validator:
        ...     def validate(self, data: str):
        ...         return True
        >>>
        >>> class EmailValidator(Validator):
        ...     pass
        >>>
        >>> class PhoneValidator(Validator):
        ...     pass
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         multibinder = self.multibinder(Validator, as_set=False)
        ...         multibinder.add(EmailValidator)  # First
        ...         multibinder.add(PhoneValidator)  # Second
        >>>
        >>> injector = get_injector(MyConfig)
        >>> validators = injector.inject(List[Validator])
        >>> len(validators)
        2
        >>> # Order is preserved
        >>> type(validators[0]).__name__
        'EmailValidator'
        >>> type(validators[1]).__name__
        'PhoneValidator'
"""

from typing import Any, Generic, List, Protocol, Set, Type, TypeVar

T = TypeVar("T", contravariant=True)


class Multibinder(Protocol, Generic[T]):
    """Protocol for binding multiple implementations of the same type.

    Multibinders allow multiple implementations of the same type to be
    registered and injected as a collection (Set or List).

    Example:
        class MyMultibinder(Multibinder[EventHandler]):
            def add(self, implementation: Type[EventHandler]) -> None:
                # Register implementation
                pass
    """

    def add(self, implementation: Type[T]) -> None:
        """Add an implementation to the multibinding.

        Args:
            implementation: The implementation class to add
        """
        ...

    def add_instance(self, instance: T) -> None:
        """Add a pre-created instance to the multibinding.

        Args:
            instance: The instance to add
        """
        ...


class SetMultibinder(Generic[T]):
    """Multibinder that binds to a Set[T].

    This multibinder collects implementations into a set, ensuring uniqueness.
    Order is not preserved.

    Example:
        >>> from pyiv.multibinder import SetMultibinder
        >>>
        >>> multibinder = SetMultibinder(EventHandler, config)
        >>> multibinder.add(EmailEventHandler)
        >>> multibinder.add(SMSEventHandler)
        >>> # Inject as Set[EventHandler]
    """

    def __init__(self, interface: Type[T], config: Any):
        """Initialize set multibinder.

        Args:
            interface: The interface type
            config: The config to register bindings with
        """
        self._interface = interface
        self._config = config
        self._implementations: Set[Type[T]] = set()
        self._instances: Set[T] = set()

    def add(self, implementation: Type[T]) -> None:
        """Add an implementation class.

        Args:
            implementation: The implementation class to add
        """
        if not isinstance(implementation, type):
            raise TypeError(f"implementation must be a type, got {type(implementation)}")
        if not issubclass(implementation, self._interface):
            raise TypeError(
                f"{implementation.__name__} must be a subclass of {self._interface.__name__}"
            )
        self._implementations.add(implementation)

    def add_instance(self, instance: T) -> None:
        """Add a pre-created instance.

        Args:
            instance: The instance to add
        """
        if not isinstance(instance, self._interface):
            raise TypeError(
                f"instance must be an instance of {self._interface.__name__}, "
                f"got {type(instance).__name__}"
            )
        self._instances.add(instance)

    def get_implementations(self) -> Set[Type[T]]:
        """Get all registered implementation classes.

        Returns:
            Set of implementation classes
        """
        return self._implementations.copy()

    def get_instances(self) -> Set[T]:
        """Get all registered instances.

        Returns:
            Set of instances
        """
        return self._instances.copy()


class ListMultibinder(Generic[T]):
    """Multibinder that binds to a List[T].

    This multibinder collects implementations into a list, preserving order.
    Duplicates are allowed.

    Example:
        >>> from pyiv.multibinder import ListMultibinder
        >>>
        >>> multibinder = ListMultibinder(Validator, config)
        >>> multibinder.add(EmailValidator)  # First
        >>> multibinder.add(PhoneValidator)  # Second
        >>> # Inject as List[Validator] - order preserved
    """

    def __init__(self, interface: Type[T], config: Any):
        """Initialize list multibinder.

        Args:
            interface: The interface type
            config: The config to register bindings with
        """
        self._interface = interface
        self._config = config
        self._implementations: List[Type[T]] = []
        self._instances: List[T] = []

    def add(self, implementation: Type[T]) -> None:
        """Add an implementation class.

        Args:
            implementation: The implementation class to add
        """
        if not isinstance(implementation, type):
            raise TypeError(f"implementation must be a type, got {type(implementation)}")
        if not issubclass(implementation, self._interface):
            raise TypeError(
                f"{implementation.__name__} must be a subclass of {self._interface.__name__}"
            )
        self._implementations.append(implementation)

    def add_instance(self, instance: T) -> None:
        """Add a pre-created instance.

        Args:
            instance: The instance to add
        """
        if not isinstance(instance, self._interface):
            raise TypeError(
                f"instance must be an instance of {self._interface.__name__}, "
                f"got {type(instance).__name__}"
            )
        self._instances.append(instance)

    def get_implementations(self) -> List[Type[T]]:
        """Get all registered implementation classes.

        Returns:
            List of implementation classes (order preserved)
        """
        return self._implementations.copy()

    def get_instances(self) -> List[T]:
        """Get all registered instances.

        Returns:
            List of instances (order preserved)
        """
        return self._instances.copy()
