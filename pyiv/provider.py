"""Provider interface for dependency injection.

This module provides the Provider interface, which is the standard way to
provide instances in dependency injection frameworks. Providers allow for
lazy initialization, injector access, and deferred creation.

**What Problem Does This Solve?**

Providers solve several common DI scenarios:

- **Lazy Initialization**: Create instances only when needed, not at injection time
- **Multiple Instances**: Get multiple instances of the same type (unlike singletons)
- **Injector Access**: Access the injector during instance creation for complex logic
- **Deferred Creation**: Delay expensive object creation until actually needed

**Real-World Use Cases:**

- Database connections that should be created on-demand, not at startup
- Services that need to create multiple instances (e.g., user sessions)
- Objects that require the injector to resolve their own dependencies dynamically

Architecture:
    - Provider: Protocol defining the provider interface (generic)
    - InjectorProvider: Provider that uses an injector to create instances
    - InstanceProvider: Provider that returns a pre-created instance
    - FactoryProvider: Provider that wraps a factory function

Usage Examples:

    Basic Provider Usage:
        >>> from pyiv.provider import Provider, InjectorProvider
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Database:
        ...     def __init__(self, connection_string: str):
        ...         self.connection_string = connection_string
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, lambda: Database("postgresql://localhost/db"))
        >>>
        >>> injector = get_injector(MyConfig)
        >>> # Create a provider for lazy initialization
        >>> db_provider = InjectorProvider(Database, injector)
        >>> # Instance is created only when get() is called
        >>> db = db_provider.get()
        >>> db.connection_string
        'postgresql://localhost/db'

    Injecting Providers:
        >>> from pyiv.provider import Provider
        >>>
        >>> class Service:
        ...     def __init__(self, db_provider: Provider[Database]):
        ...         self._db_provider = db_provider
        ...
        ...     def do_work(self):
        ...         # Create database connection only when needed
        ...         db = self._db_provider.get()
        ...         return db.connection_string
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, lambda: Database("postgresql://localhost/db"))
        ...         self.register(Service, Service)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> service = injector.inject(Service)
        >>> service.do_work()
        'postgresql://localhost/db'

    Using InstanceProvider for Pre-Created Instances:
        >>> from pyiv.provider import InstanceProvider
        >>>
        >>> class FileLogger:
        ...     pass
        >>> logger = FileLogger()
        >>> logger_provider = InstanceProvider(logger)
        >>> logger_provider.get() is logger
        True
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Optional, Protocol, Type, TypeVar, Union

from pyiv.key import Key

T = TypeVar("T", covariant=True)


class Provider(Protocol, Generic[T]):
    """Protocol for provider implementations.

    **Why this exists:** Lazy or repeated creation of a type without constructing it at inject() time; inject Provider[T] instead of T.

    Providers are used to supply instances of a specific type, allowing for
    customized creation logic, lazy initialization, and injector access.

    This is the standard pattern in dependency injection frameworks for
    providing instances. Providers can be injected themselves, allowing
    for lazy initialization and multiple instance creation.

    Example:
        >>> from pyiv.provider import Provider
        >>> from pyiv import Config, Injector, get_injector
        >>>
        >>> class Database:
        ...     pass
        >>>
        >>> class DatabaseProvider:
        ...     def __init__(self, injector: Injector):
        ...         self._injector = injector
        ...
        ...     def get(self) -> Database:
        ...         return self._injector.inject(Database)
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, Database)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> provider: Provider[Database] = DatabaseProvider(injector)
        >>> isinstance(provider.get(), Database)
        True
    """

    def get(self) -> T:
        """Get an instance of type T.

        Returns:
            An instance of type T
        """
        ...


class BaseProvider(ABC, Generic[T]):
    """Abstract base class for provider implementations.

    **Why this exists:** Subclassable provider when you need a real class the injector can construct.

    Provides a concrete base class for providers that need to be
    instantiated. Subclasses should implement the `get()` method.

    Example:
        >>> from pyiv.provider import BaseProvider, InstanceProvider
        >>>
        >>> class User:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>>
        >>> class UserProvider(BaseProvider[User]):
        ...     def get(self) -> User:
        ...         return User("alice")
        >>>
        >>> UserProvider().get().name
        'alice'
        >>> InstanceProvider(User("bob")).get().name
        'bob'
    """

    @abstractmethod
    def get(self) -> T:
        """Get an instance of type T.

        Returns:
            An instance of type T
        """
        pass


class InjectorProvider(Generic[T]):
    """Provider that uses an injector to create instances.

    This provider wraps an injector and a type or :class:`~pyiv.key.Key`,
    delegating instance creation to the injector. Useful for lazy lookup
    and for ``Annotated[Provider[T], Named(...)]`` constructor params
    (field / members injection does not unwrap that Annotated form).

    **Why this exists:** Provider that asks an Injector for T (or a qualified
    Key) on each get() — lazy graph lookup.


    Example:
        >>> from pyiv import Config, get_injector
        >>> from pyiv.key import Key, Named
        >>> from pyiv.provider import InjectorProvider
        >>>
        >>> class Database:
        ...     def __init__(self, name: str = "default"):
        ...         self.name = name
        >>>
        >>> class PostgreSQL(Database):
        ...     def __init__(self):
        ...         super().__init__("postgresql")
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Database, Database)
        ...         self.register_key(Key(Database, Named("primary")), PostgreSQL)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> db_provider = InjectorProvider(Database, injector)
        >>> isinstance(db_provider.get(), Database)
        True
        >>> named = InjectorProvider(Key(Database, Named("primary")), injector)
        >>> named.get().name
        'postgresql'
    """

    def __init__(
        self,
        cls_or_key: Union[Type[T], Key[T]],
        injector: Any,
        *,
        from_: Optional[Type] = None,
    ):
        """Initialize provider with a type or Key and injector.

        Args:
            cls_or_key: The type or qualified Key to provide instances of
            injector: The injector to use for instance creation
            from_: Optional requesting type for contextual bindings (bare types only)
        """
        self._cls = cls_or_key
        self._injector = injector
        self._from = from_

    def get(self) -> T:
        """Get an instance using the injector.

        Returns:
            An instance created by ``injector.inject`` of the type or Key
        """
        if self._from is not None and not isinstance(self._cls, Key):
            return self._injector.inject(self._cls, from_=self._from)
        return self._injector.inject(self._cls)


class InstanceProvider(Generic[T]):
    """Provider that returns a pre-created instance.

    **Why this exists:** Wrap an already-built object as a Provider for binder.to_provider / register_provider.

    This provider simply returns the same instance every time get() is called.
    Useful for wrapping pre-created singletons or instances.

    Example:
        >>> from pyiv.provider import InstanceProvider
        >>>
        >>> class Logger:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>>
        >>> my_logger = Logger("app")
        >>> logger_provider = InstanceProvider(my_logger)
        >>> logger = logger_provider.get()  # Returns my_logger
        >>> logger is my_logger
        True
        >>> logger.name
        'app'
    """

    def __init__(self, instance: T):
        """Initialize provider with a pre-created instance.

        Args:
            instance: The instance to return
        """
        self._instance = instance

    def get(self) -> T:
        """Get the pre-created instance.

        Returns:
            The instance that was provided during initialization
        """
        return self._instance


class FactoryProvider(Generic[T]):
    """Provider that wraps a factory function.

    **Why this exists:** Adapt a zero-arg factory callable into the Provider protocol.

    This provider calls a factory function each time get() is called.
    Useful for creating new instances on demand.

    Example:
        >>> from pyiv.provider import FactoryProvider
        >>>
        >>> class User:
        ...     def __init__(self, name: str = "default"):
        ...         self.name = name
        >>>
        >>> def create_user() -> User:
        ...     return User(name="default")
        >>>
        >>> user_provider = FactoryProvider(create_user)
        >>> user = user_provider.get()  # Calls create_user()
        >>> user.name
        'default'
        >>> # Each call creates a new instance
        >>> user2 = user_provider.get()
        >>> user is not user2
        True
    """

    def __init__(self, factory: Callable[..., T]):
        """Initialize provider with a factory function.

        Args:
            factory: A callable that creates instances of type T
        """
        self._factory = factory

    def get(self) -> T:
        """Get an instance by calling the factory function.

        Returns:
            An instance created by the factory function
        """
        return self._factory()
