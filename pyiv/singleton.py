"""Singleton management for dependency injection."""

from enum import Enum
from typing import Dict, Type, Any
import threading


class SingletonType(Enum):
    """Type of singleton behavior for registered dependencies.
    
    Attributes:
        NONE: No singleton behavior - new instance created each time
        SINGLETON: Per-injector singleton - one instance per Injector instance
        GLOBAL_SINGLETON: Global singleton - one instance shared across all injectors (thread-safe)
    """
    NONE = "none"
    SINGLETON = "singleton"
    GLOBAL_SINGLETON = "global_singleton"


class GlobalSingletonRegistry:
    """Thread-safe registry for global singletons.
    
    This registry stores singleton instances that are shared across
    all injector instances. Access is thread-safe.
    """
    
    _lock = threading.Lock()
    _instances: Dict[Type, Any] = {}
    
    @classmethod
    def get(cls, abstract: Type) -> Any:
        """Get a global singleton instance.
        
        Args:
            abstract: The abstract type to retrieve
            
        Returns:
            The singleton instance or None if not registered
        """
        with cls._lock:
            return cls._instances.get(abstract)
    
    @classmethod
    def set(cls, abstract: Type, instance: Any) -> None:
        """Set a global singleton instance.
        
        Args:
            abstract: The abstract type
            instance: The instance to store
        """
        with cls._lock:
            cls._instances[abstract] = instance
    
    @classmethod
    def has(cls, abstract: Type) -> bool:
        """Check if a global singleton exists.
        
        Args:
            abstract: The abstract type to check
            
        Returns:
            True if a singleton exists, False otherwise
        """
        with cls._lock:
            return abstract in cls._instances
    
    @classmethod
    def clear(cls) -> None:
        """Clear all global singletons (useful for testing)."""
        with cls._lock:
            cls._instances.clear()



