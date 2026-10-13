"""Reflection-based discovery for dependency injection.

This module provides functionality to automatically discover interface
implementations in Python packages using reflection, eliminating the need
for manual registration.

**What Problem Does This Solve?**

Plugin-style packages accumulate many implementations. Hand-registering each
class is brittle; scanning a package once keeps discovery in DI. For catalogs
(recipes, tools, handlers), opt into ``as_multibind`` so every discovered
class joins a map/set/list multibind instead of last-wins unqualified
``register``.

**Real-World Use Cases:**
- Scan ``myapp.handlers`` for ``*Handler`` classes
- Fill a recipe catalog via ``as_multibind="map"`` and ``key_attr="name"``
- Accumulate list/set multibinds across ``install`` of several packages

Architecture:
    - ReflectionConfig: Config subclass with ``register_module`` discovery
    - Legacy path: each discovery calls ``register`` (last implementation wins)
    - Catalog path: ``as_multibind`` contributes to map/set/list multibinds

Usage Examples:

    Scan A Package Into A Map Catalog:

        >>> import sys, types
        >>> from pyiv import get_injector
        >>> from pyiv.reflection import ReflectionConfig
        >>> class Recipe:
        ...     name = "base"
        >>> pkg = types.ModuleType("doctest_catalog_recipes")
        >>> class HarnessRun(Recipe):
        ...     name = "harness_run"
        >>> class VerifyRepair(Recipe):
        ...     name = "verify_repair"
        >>> HarnessRun.__module__ = "doctest_catalog_recipes"
        >>> VerifyRepair.__module__ = "doctest_catalog_recipes"
        >>> pkg.HarnessRun = HarnessRun
        >>> pkg.VerifyRepair = VerifyRepair
        >>> sys.modules["doctest_catalog_recipes"] = pkg
        >>> class RecipeConfig(ReflectionConfig):
        ...     def configure(self):
        ...         self.register_module(
        ...             Recipe,
        ...             "doctest_catalog_recipes",
        ...             as_multibind="map",
        ...             key_attr="name",
        ...             recursive=False,
        ...         )
        >>> sorted(get_injector(RecipeConfig).catalog_keys(Recipe))
        ['harness_run', 'verify_repair']
"""

import fnmatch
import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Type

from pyiv.config import Config, MapConflictPolicy
from pyiv.singleton import SingletonType

AsMultibindMode = Literal["map", "set", "list"]


class ReflectionConfig(Config):
    """Configuration that discovers implementations in packages via reflection.

    **Why this exists:** Auto-discover interface implementations in a package
    instead of listing every class. Use ``as_multibind`` when discoveries must
    accumulate into a catalog (map/set/list) rather than overwrite a single
    unqualified binding.

    Example:
        >>> import sys, types
        >>> from pyiv import get_injector
        >>> from pyiv.reflection import ReflectionConfig
        >>> class Tool:
        ...     name = "base"
        >>> pkg = types.ModuleType("doctest_tools_pkg")
        >>> class GrepTool(Tool):
        ...     name = "grep"
        >>> class LintTool(Tool):
        ...     name = "lint"
        >>> GrepTool.__module__ = "doctest_tools_pkg"
        >>> LintTool.__module__ = "doctest_tools_pkg"
        >>> pkg.GrepTool = GrepTool
        >>> pkg.LintTool = LintTool
        >>> sys.modules["doctest_tools_pkg"] = pkg
        >>> class ToolConfig(ReflectionConfig):
        ...     def configure(self):
        ...         self.register_module(
        ...             Tool,
        ...             "doctest_tools_pkg",
        ...             pattern="*Tool",
        ...             as_multibind="map",
        ...             key_attr="name",
        ...             recursive=False,
        ...         )
        >>> get_injector(ToolConfig).catalog_keys(Tool)
        ['grep', 'lint']
    """

    def __init__(self):
        """Initialize the reflection configuration.

        ``_module_registrations`` must exist before ``Config.__init__`` runs
        ``configure()``, which may call :meth:`register_module`.
        """
        self._module_registrations: Dict[Type, Dict[str, Any]] = {}
        super().__init__()

    def register_module(
        self,
        interface: Type,
        package_path: str,
        pattern: Optional[str] = None,
        recursive: bool = True,
        singleton_type: SingletonType = SingletonType.SINGLETON,
        *,
        as_multibind: Optional[AsMultibindMode] = None,
        key_attr: Optional[str] = None,
        on_conflict: MapConflictPolicy = "error",
    ):
        """Register a package to scan for interface implementations.

        Args:
            interface: The abstract class or interface to find implementations of
            package_path: Python package path (e.g., "my_service.mcp.handlers")
            pattern: Optional name pattern for filtering (e.g. ``*Handler``,
                ``handle_*``). Uses fnmatch syntax. If None, all implementations
                are discovered.
            recursive: Whether to scan submodules recursively (default: True)
            singleton_type: How to handle instances on the legacy unqualified
                ``register`` path (ignored when ``as_multibind`` is set)
            as_multibind: If ``None`` (default), each discovery calls
                ``register(interface, impl)`` (last wins). If ``"map"``,
                ``"set"``, or ``"list"``, discoveries join that multibind only
                and do not overwrite the unqualified binding.
            key_attr: Class attribute name used as the map key when
                ``as_multibind="map"`` (required in that mode)
            on_conflict: Conflict policy for map multibind contributions
                (default ``"error"`` so duplicate catalog ids fail loudly)

        Raises:
            TypeError: If interface is not a type
            ImportError: If the package cannot be imported
            ValueError: If map mode lacks ``key_attr`` or a class lacks the attr

        Example:
            >>> import sys, types
            >>> from pyiv.reflection import ReflectionConfig
            >>> class Handler:
            ...     pass
            >>> pkg = types.ModuleType("doctest_handler_list")
            >>> class CreateHandler(Handler):
            ...     pass
            >>> class UpdateHandler(Handler):
            ...     pass
            >>> CreateHandler.__module__ = "doctest_handler_list"
            >>> UpdateHandler.__module__ = "doctest_handler_list"
            >>> pkg.CreateHandler = CreateHandler
            >>> pkg.UpdateHandler = UpdateHandler
            >>> sys.modules["doctest_handler_list"] = pkg
            >>> class ListConfig(ReflectionConfig):
            ...     def configure(self):
            ...         self.register_module(
            ...             Handler,
            ...             "doctest_handler_list",
            ...             pattern="*Handler",
            ...             as_multibind="list",
            ...             recursive=False,
            ...         )
            >>> mb = ListConfig().get_multibinding(Handler)
            >>> sorted(c.__name__ for c in mb[1])
            ['CreateHandler', 'UpdateHandler']
        """
        if not isinstance(interface, type):
            raise TypeError(f"interface must be a type, got {type(interface)}")
        if as_multibind is not None and as_multibind not in ("map", "set", "list"):
            raise ValueError(
                f"as_multibind must be None, 'map', 'set', or 'list', got {as_multibind!r}"
            )
        if as_multibind == "map" and not key_attr:
            raise ValueError("key_attr is required when as_multibind='map'")

        # Store registration for later discovery
        self._module_registrations[interface] = {
            "package": package_path,
            "pattern": pattern,
            "recursive": recursive,
            "singleton_type": singleton_type,
            "as_multibind": as_multibind,
            "key_attr": key_attr,
            "on_conflict": on_conflict,
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
        as_multibind: Optional[AsMultibindMode] = reg.get("as_multibind")
        singleton_type = reg.get("singleton_type", SingletonType.SINGLETON)

        if as_multibind is None:
            for _name, impl_class in implementations.items():
                self.register(interface, impl_class, singleton_type=singleton_type)
            return

        if as_multibind == "map":
            key_attr = reg["key_attr"]
            on_conflict: MapConflictPolicy = reg.get("on_conflict", "error")
            for _name, impl_class in implementations.items():
                if not hasattr(impl_class, key_attr):
                    raise ValueError(
                        f"{impl_class.__name__} has no attribute {key_attr!r} "
                        f"required for as_multibind='map'"
                    )
                key = getattr(impl_class, key_attr)
                self.contribute_map(interface, key, impl_class, on_conflict=on_conflict)
            return

        as_set = as_multibind == "set"
        for _name, impl_class in implementations.items():
            self.register_multibinding(interface, impl_class, as_set=as_set)

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
            package: The package to get submodules from
            package_path: The package path string

        Returns:
            Dictionary mapping submodule names to modules
        """
        submodules: Dict[str, Any] = {}

        if not hasattr(package, "__file__") or package.__file__ is None:
            return submodules

        package_dir = Path(package.__file__).parent

        # Find all .py files in the package directory
        for py_file in package_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            module_name = py_file.stem
            full_module_path = f"{package_path}.{module_name}"

            try:
                submodule = importlib.import_module(full_module_path)
                submodules[module_name] = submodule
            except ImportError:
                # Skip modules that can't be imported
                continue

        # Also check for subpackages (directories with __init__.py)
        for item in package_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                subpackage_name = item.name
                full_subpackage_path = f"{package_path}.{subpackage_name}"

                try:
                    subpackage = importlib.import_module(full_subpackage_path)
                    submodules[subpackage_name] = subpackage
                except ImportError:
                    # Skip packages that can't be imported
                    continue

        return submodules

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a name matches a pattern using fnmatch.

        Args:
            name: The name to check
            pattern: The pattern to match against

        Returns:
            True if the name matches the pattern
        """
        return fnmatch.fnmatch(name, pattern)
