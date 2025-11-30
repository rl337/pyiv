"""Reflection-based discovery for dependency injection.

This module provides functionality to automatically discover interface implementations
in Python packages using reflection, eliminating the need for manual registration.
"""

import fnmatch
import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pyiv.config import Config
from pyiv.singleton import SingletonType


class ReflectionConfig(Config):
    """Configuration class that supports module-based discovery of implementations.

    This class extends Config to add reflection-based discovery capabilities.
    Instead of manually registering each implementation, you can register a package
    to scan, and all implementations of an interface will be automatically discovered
    and registered.

    Example:
        class MyConfig(ReflectionConfig):
            def configure(self):
                # Register module for handler discovery
                self.register_module(
                    IHandler,
                    "my_service.handlers",
                    pattern="*Handler",
                    singleton_type=SingletonType.SINGLETON
                )
    """

    def __init__(self):
        """Initialize the reflection configuration."""
        super().__init__()
        self._module_registrations: Dict[Type, Dict[str, Any]] = {}

    def register_module(
        self,
        interface: Type,
        package_path: str,
        pattern: Optional[str] = None,
        recursive: bool = True,
        singleton_type: SingletonType = SingletonType.SINGLETON,
    ):
        """Register a package to scan for interface implementations.

        Args:
            interface: The abstract class or interface to find implementations of
            package_path: Python package path (e.g., "my_service.mcp.handlers")
            pattern: Optional name pattern for filtering (e.g., "*Handler", "handle_*")
                     Uses fnmatch syntax. If None, all implementations are discovered.
            recursive: Whether to scan submodules recursively (default: True)
            singleton_type: How to handle instances (default: SINGLETON for per-injector reuse)

        Raises:
            TypeError: If interface is not a type
            ImportError: If the package cannot be imported

        Example:
            # Discover all classes ending in "Handler" that implement IHandler
            self.register_module(
                IHandler,
                "my_service.handlers",
                pattern="*Handler"
            )

            # Discover all implementations recursively
            self.register_module(
                IService,
                "my_service.services",
                recursive=True
            )
        """
        if not isinstance(interface, type):
            raise TypeError(f"interface must be a type, got {type(interface)}")

        # Store registration for later discovery
        self._module_registrations[interface] = {
            "package": package_path,
            "pattern": pattern,
            "recursive": recursive,
            "singleton_type": singleton_type,
        }

        # Trigger discovery and registration immediately
        # This ensures implementations are available when injector is created
        self._discover_and_register(interface)

    def discover_implementations(self, interface: Type) -> Dict[str, Type]:
        """Discover all implementations of an interface in registered modules.

        This method scans the registered package for classes that implement
        the given interface. Only classes within the specified package (and
        optionally submodules) are discovered - no discovery happens outside
        the registered package boundaries.

        Args:
            interface: The interface to discover implementations for

        Returns:
            Dictionary mapping implementation names to classes.
            Keys are class names (or "submodule.ClassName" for submodules).

        Raises:
            ValueError: If no module registration exists for the interface
            ImportError: If the package cannot be imported
        """
        if interface not in self._module_registrations:
            return {}

        reg = self._module_registrations[interface]
        package_path = reg["package"]

        try:
            package = importlib.import_module(package_path)
        except ImportError as e:
            raise ImportError(
                f"Cannot import package '{package_path}' for interface {interface.__name__}: {e}"
            ) from e

        implementations = {}

        # Scan the main module for implementations
        for name, obj in inspect.getmembers(package):
            if self._is_implementation(obj, interface, reg["pattern"], package_path):
                implementations[name] = obj

        # Recursively scan submodules if requested
        if reg["recursive"]:
            self._scan_submodules_recursive(
                package, package_path, interface, reg, implementations, package_path
            )

        return implementations

    def _discover_and_register(self, interface: Type):
        """Discover implementations and register them with singleton configuration.

        This is called automatically when register_module() is invoked.

        Args:
            interface: The interface to discover and register implementations for
        """
        implementations = self.discover_implementations(interface)
        reg = self._module_registrations[interface]
        singleton_type = reg.get("singleton_type", SingletonType.SINGLETON)

        # Register each discovered implementation with singleton configuration
        for name, impl_class in implementations.items():
            # Register the implementation class with the interface
            # This enables inject() and inject_by_name() to work
            self.register(interface, impl_class, singleton_type=singleton_type)

    def _is_implementation(
        self,
        obj: Any,
        interface: Type,
        pattern: Optional[str],
        current_module_path: Optional[str] = None,
    ) -> bool:
        """Check if an object implements the interface.

        Args:
            obj: The object to check (class, function, etc.)
            interface: The interface to check against
            pattern: Optional name pattern to match
            current_module_path: The module path currently being scanned (for validation)

        Returns:
            True if the object is a valid implementation, False otherwise
        """
        # Must be a class
        if not inspect.isclass(obj):
            return False

        # Must implement the interface (but not be the interface itself)
        if not issubclass(obj, interface) or obj == interface:
            return False

        # Check name pattern if provided
        if pattern:
            if not self._matches_pattern(obj.__name__, pattern):
                return False

        # Must be defined in the current module being scanned (not imported from elsewhere)
        # This ensures we only discover implementations that are actually defined in
        # the module being scanned, preventing duplicates when classes are re-exported
        if not self._is_in_module(obj, current_module_path, interface):
            return False

        return True

    def _is_in_module(self, obj: Any, current_module_path: Optional[str], interface: Type) -> bool:
        """Check if an object is defined in the specific module being scanned.

        This prevents discovering classes that are imported from other modules,
        even within the same package. When a class is imported and re-exported
        in multiple modules, we only want to discover it once from the module
        where it's actually defined.

        Args:
            obj: The class to check
            current_module_path: The module path currently being scanned
            interface: The interface (used to get the registered package path)

        Returns:
            True if the object is defined in the current module, False otherwise
        """
        # Get the module where the class is actually defined
        obj_module = getattr(obj, "__module__", None)
        if obj_module is None:
            return False

        # If we have a current module path, verify exact match
        # This ensures we only discover classes defined in the specific module
        # being scanned, not classes imported from other modules
        if current_module_path is not None:
            return obj_module == current_module_path

        # Fallback: check if it's in the registered package (for backward compatibility)
        if interface not in self._module_registrations:
            return False

        reg = self._module_registrations[interface]
        package_path = reg["package"]
        recursive = reg.get("recursive", True)

        # Exact match: class is in the registered package
        if obj_module == package_path:
            return True

        # If recursive, check if it's in a submodule
        if recursive:
            # Check if the class's module starts with the registered package path
            # and is a submodule (has a dot after the package path)
            if obj_module.startswith(package_path + "."):
                return True

        return False

    def _scan_submodules_recursive(
        self,
        package: Any,
        package_path: str,
        interface: Type,
        reg: Dict[str, Any],
        implementations: Dict[str, Type],
        root_package_path: Optional[str] = None,
    ):
        """Recursively scan submodules for implementations.

        Args:
            package: The package/module to scan
            package_path: The package path string (full path from root)
            interface: The interface to find implementations for
            reg: Registration configuration
            implementations: Dictionary to add discovered implementations to
            root_package_path: The root package path (for building full names)
        """
        # Track root package path for building full names
        if root_package_path is None:
            root_package_path = package_path

        submodules = self._get_submodules(package, package_path)
        for submodule_name, submodule in submodules.items():
            # Build full path from root for this submodule
            full_submodule_path = f"{package_path}.{submodule_name}"
            # Build relative path from root package for naming
            if full_submodule_path.startswith(root_package_path):
                relative_path = full_submodule_path[len(root_package_path) + 1 :]
            else:
                relative_path = submodule_name

            # Scan this submodule for implementations
            for name, obj in inspect.getmembers(submodule):
                if self._is_implementation(obj, interface, reg["pattern"], full_submodule_path):
                    # Use full path from root package to avoid collisions
                    # e.g., "pkg.mod.ClassA" vs "pkg.sub.mod.ClassA"
                    full_name = f"{relative_path}.{name}" if relative_path else name
                    implementations[full_name] = obj

            # Recursively scan nested submodules
            self._scan_submodules_recursive(
                submodule,
                full_submodule_path,
                interface,
                reg,
                implementations,
                root_package_path,
            )

    def _get_submodules(self, package: Any, package_path: str) -> Dict[str, Any]:
        """Get all submodules of a package.

        Args:
            package: The package module to scan
            package_path: The package path string

        Returns:
            Dictionary mapping submodule names to module objects
        """
        submodules: Dict[str, Any] = {}

        # Get the package's directory path
        package_file = getattr(package, "__file__", None)
        if package_file is None:
            return submodules

        package_dir = Path(package_file).parent

        # Scan for Python files in the package directory
        for py_file in package_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            module_name = py_file.stem
            submodule_path = f"{package_path}.{module_name}"

            try:
                submodule = importlib.import_module(submodule_path)
                submodules[module_name] = submodule
            except ImportError:
                # Skip modules that can't be imported
                continue

        # Also check for subdirectories with __init__.py
        for subdir in package_dir.iterdir():
            if not subdir.is_dir():
                continue

            init_file = subdir / "__init__.py"
            if not init_file.exists():
                continue

            module_name = subdir.name
            submodule_path = f"{package_path}.{module_name}"

            try:
                submodule = importlib.import_module(submodule_path)
                submodules[module_name] = submodule
            except ImportError:
                # Skip modules that can't be imported
                continue

        return submodules

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a name matches a pattern using fnmatch syntax.

        Args:
            name: The name to check
            pattern: The pattern to match against (supports * wildcard)

        Returns:
            True if the name matches the pattern, False otherwise
        """
        return fnmatch.fnmatch(name, pattern)
