"""pyiv - A lightweight dependency injection library for Python."""

from pyiv.clock import Clock, RealClock, SyntheticClock, Timer
from pyiv.config import Config
from pyiv.datetime_service import DateTimeService, MockDateTimeService, PythonDateTimeService
from pyiv.factory import BaseFactory, Factory, SimpleFactory
from pyiv.filesystem import Filesystem, MemoryFilesystem, RealFilesystem
from pyiv.injector import Injector, get_injector
from pyiv.reflection import ReflectionConfig
from pyiv.singleton import GlobalSingletonRegistry, SingletonType

# Command interface (optional import)
try:
    from pyiv.command import CLICommand, Command, CommandRunner, ServiceCommand

    _has_commands = True
except ImportError:
    _has_commands = False

__version__ = "0.2.4"
__all__ = [
    "Config",
    "ReflectionConfig",
    "Injector",
    "get_injector",
    "Filesystem",
    "RealFilesystem",
    "MemoryFilesystem",
    "Clock",
    "RealClock",
    "SyntheticClock",
    "Timer",
    "DateTimeService",
    "PythonDateTimeService",
    "MockDateTimeService",
    "Factory",
    "BaseFactory",
    "SimpleFactory",
    "SingletonType",
    "GlobalSingletonRegistry",
]

if _has_commands:
    __all__.extend(["Command", "ServiceCommand", "CLICommand", "CommandRunner"])
