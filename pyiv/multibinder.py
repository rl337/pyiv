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
    - MapMultibinder: Binds to a Dict[K, V] (keyed implementations)

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
        >>> class HandlerHost:
        ...     def __init__(self, handlers: Set[EventHandler]):
        ...         self.handlers = handlers
        >>> handlers = injector.inject(HandlerHost).handlers
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
        >>> class ValidatorHost:
        ...     def __init__(self, validators: List[Validator]):
        ...         self.validators = validators
        >>> validators = injector.inject(ValidatorHost).validators
        >>> len(validators)
        2
        >>> type(validators[0]).__name__
        'EmailValidator'
        >>> type(validators[1]).__name__
        'PhoneValidator'

    Using MapMultibinder (Keyed Implementations):
        >>> from typing import Dict
        >>> from pyiv import Config, get_injector
        >>> class Encoder:
        ...     def encode(self, data: str) -> str:
        ...         return data
        >>> class JsonEncoder(Encoder):
        ...     def encode(self, data: str) -> str:
        ...         return f"json:{data}"
        >>> class XmlEncoder(Encoder):
        ...     def encode(self, data: str) -> str:
        ...         return f"xml:{data}"
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         mb = self.map_multibinder(Encoder)
        ...         mb.add("json", JsonEncoder)
        ...         mb.add("xml", XmlEncoder)
        >>> class EncoderHost:
        ...     def __init__(self, encoders: Dict[str, Encoder]):
        ...         self.encoders = encoders
        >>> encoders = get_injector(MyConfig).inject(EncoderHost).encoders
        >>> sorted(encoders.keys())
        ['json', 'xml']
        >>> encoders["json"].encode("x")
        'json:x'
"""

from typing import Any, Dict, Generic, Hashable, List, Protocol, Set, Type, TypeVar

K = TypeVar("K", bound=Hashable)
T = TypeVar("T", contravariant=True)
V = TypeVar("V")


class Multibinder(Protocol, Generic[T]):
    """Protocol for binding multiple implementations of the same type.

    **Why this exists:** Register many implementations of one type for injection as a collection.

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

    **Why this exists:** Collect unique implementations as Set[T] (order not preserved).

    This multibinder collects implementations into a set, ensuring uniqueness.
    Order is not preserved.

    Example:
        >>> from pyiv import Config
        >>> class EventHandler:
        ...     pass
        >>> class EmailEventHandler(EventHandler):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         pass
        >>> multibinder = SetMultibinder(EventHandler, MyConfig())
        >>> multibinder.add(EmailEventHandler)
        >>> EmailEventHandler in multibinder.get_implementations()
        True
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
        self._config.register_multibinding(self._interface, implementation, as_set=True)

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
        self._config.register_multibinding_instance(self._interface, instance, as_set=True)

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

    **Why this exists:** Collect implementations as List[T] preserving add order.

    This multibinder collects implementations into a list, preserving order.
    Duplicates are allowed.

    Example:
        >>> from pyiv import Config
        >>>
        >>> class Validator:
        ...     pass
        >>> class EmailValidator(Validator):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         pass
        >>> multibinder = ListMultibinder(Validator, MyConfig())
        >>> multibinder.add(EmailValidator)
        >>> EmailValidator in multibinder.get_implementations()
        True
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
        self._config.register_multibinding(self._interface, implementation, as_set=False)

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
        self._config.register_multibinding_instance(self._interface, instance, as_set=False)

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


class MapMultibinder(Generic[K, V]):
    """Multibinder that binds to a Dict[K, V].

    **Why this exists:** Collect keyed implementations for Dict[K, V] injection.

    Collects keyed implementations for injection as a mapping. Inject the
    dict through a host class constructor, not ``injector.inject(Dict[...])``.

    Example:
        >>> from typing import Dict
        >>> from pyiv import Config, get_injector
        >>> class Plugin:
        ...     pass
        >>> class AuthPlugin(Plugin):
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.map_multibinder(Plugin).add("auth", AuthPlugin)
        >>> class Host:
        ...     def __init__(self, plugins: Dict[str, Plugin]):
        ...         self.plugins = plugins
        >>> "auth" in get_injector(MyConfig).inject(Host).plugins
        True
    """

    def __init__(self, value_type: Type[V], config: Any):
        self._value_type = value_type
        self._config = config
        self._implementations: Dict[K, Type[V]] = {}
        self._instances: Dict[K, V] = {}

    def add(self, key: K, implementation: Type[V]) -> None:
        """Add a keyed implementation class."""
        if not isinstance(implementation, type):
            raise TypeError(f"implementation must be a type, got {type(implementation)}")
        if not issubclass(implementation, self._value_type):
            raise TypeError(
                f"{implementation.__name__} must be a subclass of {self._value_type.__name__}"
            )
        self._implementations[key] = implementation
        self._config.register_map_multibinding(self._value_type, key, implementation)

    def add_instance(self, key: K, instance: V) -> None:
        """Add a keyed pre-created instance."""
        if not isinstance(instance, self._value_type):
            raise TypeError(
                f"instance must be an instance of {self._value_type.__name__}, "
                f"got {type(instance).__name__}"
            )
        self._instances[key] = instance
        self._config.register_map_multibinding_instance(self._value_type, key, instance)

    def get_implementations(self) -> Dict[K, Type[V]]:
        """Get all registered keyed implementation classes."""
        return dict(self._implementations)

    def get_instances(self) -> Dict[K, V]:
        """Get all registered keyed instances."""
        return dict(self._instances)
