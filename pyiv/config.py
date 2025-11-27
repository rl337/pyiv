"""Configuration base class for dependency injection."""

from typing import Any, Callable, Dict, Optional, Type, Union

from pyiv.singleton import SingletonType


class Config:
    """Base class for dependency injection configuration.

    Subclasses should override `configure()` to register dependencies.
    """

    def __init__(self):
        """Initialize the configuration."""
        self._registrations: Dict[Type, Union[Type, Any, Callable]] = {}
        self._instances: Dict[Type, Any] = {}
        self._singleton_types: Dict[Type, SingletonType] = {}
        self.configure()

    def configure(self):
        """Override this method to register dependencies.

        Example:
            def configure(self):
                self.register(AbstractClass, ConcreteClass)
                self.register_instance(Logger, my_logger_instance)
        """
        pass