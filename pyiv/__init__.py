"""pyiv - A lightweight dependency injection library for Python."""

from pyiv.config import Config
from pyiv.injector import Injector, get_injector
from pyiv.filesystem import Filesystem, RealFilesystem, MemoryFilesystem
from pyiv.clock import Clock, RealClock, SyntheticClock, Timer
from pyiv.factory import Factory, BaseFactory, SimpleFactory
from pyiv.singleton import SingletonType, GlobalSingletonRegistry

__version__ = "0.1.0"
__all__ = [
    "Config",
    "Injector",
    "get_injector",
    "Filesystem",
    "RealFilesystem",
    "MemoryFilesystem",
    "Clock",
    "RealClock",
    "SyntheticClock",
    "Timer",
    "Factory",
    "BaseFactory",
    "SimpleFactory",
    "SingletonType",
    "GlobalSingletonRegistry",
]

