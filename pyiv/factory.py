"""Factory pattern support for dependency injection."""

from typing import Protocol, TypeVar, Generic, Any, Callable, Optional
from abc import ABC, abstractmethod

T = TypeVar('T', covariant=True)


class Factory(Protocol, Generic[T]):
    """Protocol for factory implementations.
    
    Factories are used to create instances of objects, typically with
    dependencies that need to be injected. This protocol defines the
    interface that factories should implement.
    
    Example:
        class DatabaseFactory(Factory[Database]):
            def create(self, connection_string: str) -> Database:
                return PostgreSQL(connection_string)
    """
    
    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create an instance of type T.
        
        Args:
            *args: Positional arguments for instance creation
            **kwargs: Keyword arguments for instance creation
            
        Returns:
            An instance of type T
        """
        ...


class BaseFactory(ABC, Generic[T]):
    """Abstract base class for factory implementations.
    
    Provides a concrete base class for factories that need to be
    instantiated. Subclasses should implement the `create()` method.
    
    Example:
        class UserFactory(BaseFactory[User]):
            def __init__(self, db: Database):
                self._db = db
            
            def create(self, name: str, email: str) -> User:
                return User(name=name, email=email, db=self._db)
    """
    
    @abstractmethod
    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create an instance of type T.
        
        Args:
            *args: Positional arguments for instance creation
            **kwargs: Keyword arguments for instance creation
            
        Returns:
            An instance of type T
        """
        pass


class SimpleFactory(Generic[T]):
    """Simple factory that wraps a callable.
    
    Useful for creating factories from functions or constructors
    without needing to define a full class.
    
    Example:
        # Factory from a function
        def create_user(name: str) -> User:
            return User(name=name)
        
        factory = SimpleFactory(create_user)
        user = factory.create("Alice")
        
        # Factory from a class constructor
        factory = SimpleFactory(PostgreSQL)
        db = factory.create(connection_string="postgresql://...")
    """
    
    def __init__(self, callable_factory: Callable[..., T]):
        """Initialize factory with a callable.
        
        Args:
            callable_factory: A callable (function, class, etc.) that creates instances
        """
        self._callable = callable_factory
    
    def create(self, *args: Any, **kwargs: Any) -> T:
        """Create an instance using the wrapped callable.
        
        Args:
            *args: Positional arguments passed to the callable
            **kwargs: Keyword arguments passed to the callable
            
        Returns:
            An instance created by the callable
        """
        return self._callable(*args, **kwargs)



