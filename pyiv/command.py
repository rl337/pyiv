"""Command interface and discovery for CLI applications.

This module provides a Command interface and automatic command discovery
using pyiv's reflection capabilities. Commands can be organized hierarchically
with commands, subcommands, and sub-subcommands.

Commands support a lifecycle pattern:
- init() - Initialize resources, configuration, etc.
- execute() - Main execution (can call run() for long-running services)
- cleanup() - Clean up resources on shutdown

Commands can optionally receive dependency injection via an injector.
"""

import argparse
import logging
import signal
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class Command(ABC):
    """Interface for CLI commands.
    
    Commands can be organized hierarchically:
    - Top-level commands (e.g., "switchboard")
    - Subcommands (e.g., "switchboard start")
    - Sub-subcommands (e.g., "switchboard agent create")
    
    Each command level can have its own arguments and execution logic.
    """
    
    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the command name.
        
        Returns:
            Command name (e.g., "switchboard", "start", "create")
        """
        pass
    
    @classmethod
    def get_description(cls) -> str:
        """Get the command description.
        
        Returns:
            Command description for help text
        """
        return ""
    
    @classmethod
    def get_aliases(cls) -> List[str]:
        """Get command aliases.
        
        Returns:
            List of alternative names for this command
        """
        return []
    
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        """Add arguments to the command's argument parser.
        
        Args:
            parser: Argument parser to add arguments to
        """
        pass
    
    @classmethod
    def get_subcommands(cls) -> List[Type['Command']]:
        """Get subcommands of this command.
        
        Returns:
            List of command classes that are subcommands of this command
        """
        return []
    
    def __init__(self, args: argparse.Namespace, injector: Optional[Any] = None):
        """Initialize the command with parsed arguments.
        
        Args:
            args: Parsed command-line arguments
            injector: Optional dependency injector for DI support
        """
        self.args = args
        self.injector = injector
        self._initialized = False
        self._shutdown_event = None
    
    def init(self) -> None:
        """Initialize the command (optional lifecycle hook).
        
        Override this method to:
        - Load configuration
        - Initialize resources (database connections, clients, etc.)
        - Set up signal handlers if needed
        - Perform any one-time setup
        
        This is called automatically by execute() before run().
        """
        pass
    
    def run(self) -> None:
        """Run the command (optional lifecycle hook for long-running services).
        
        Override this method for long-running services that need a main loop.
        For one-shot commands, override execute() directly instead.
        
        This method should:
        - Start the main service loop
        - Block until service should stop
        - Handle the primary service functionality
        
        This method should check self._shutdown_event periodically
        and exit gracefully when shutdown is requested.
        """
        pass
    
    @abstractmethod
    def execute(self) -> int:
        """Execute the command.
        
        For long-running services, this typically calls:
        1. init() - Initialize resources
        2. run() - Main service loop
        3. cleanup() - Clean up resources
        
        For one-shot commands, implement the logic directly here.
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        pass
    
    def cleanup(self) -> None:
        """Cleanup after command execution (optional lifecycle hook).
        
        Override this method to:
        - Close database connections
        - Stop background tasks
        - Clean up any resources
        - Perform graceful shutdown
        
        Called after execute() completes, even if an exception occurs.
        """
        pass
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown.
        
        Call this in init() for long-running services that need graceful shutdown.
        """
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            if self._shutdown_event:
                self._shutdown_event.set()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)


class ServiceCommand(Command):
    """Base class for long-running service commands.
    
    Provides a standard lifecycle pattern:
    1. init() - Initialize resources, configuration, etc.
    2. run() - Main service loop (blocking)
    3. cleanup() - Clean up resources on shutdown
    
    Subclasses should override init(), run(), and cleanup().
    """
    
    def execute(self) -> int:
        """Execute the service command lifecycle.
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            # Initialize
            logger.info(f"Initializing {self.get_name()}...")
            self.init()
            self._initialized = True
            logger.info(f"{self.get_name()} initialized successfully")
            
            # Run
            logger.info(f"Starting {self.get_name()}...")
            self.run()
            logger.info(f"{self.get_name()} stopped")
            
            return 0
            
        except KeyboardInterrupt:
            logger.info(f"{self.get_name()} interrupted by user")
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            logger.error(f"Error in {self.get_name()}: {e}", exc_info=True)
            return 1
        finally:
            # Cleanup
            if self._initialized:
                try:
                    logger.info(f"Cleaning up {self.get_name()}...")
                    self.cleanup()
                    logger.info(f"{self.get_name()} cleanup complete")
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}", exc_info=True)


class CLICommand(Command):
    """Base class for one-shot CLI commands (not long-running services).
    
    Provides a simplified lifecycle for commands that execute and exit:
    1. init() - Optional initialization
    2. execute() - Main command logic (subclasses override this)
    3. cleanup() - Optional cleanup
    
    Subclasses should override execute() to implement command logic.
    For commands that need init/run/cleanup, override those methods instead.
    """
    
    def __init__(self, args: argparse.Namespace, injector: Optional[Any] = None):
        """Initialize CLI command with parsed arguments."""
        super().__init__(args, injector)
        self._exit_code: Optional[int] = None
    
    def init(self) -> None:
        """Initialize CLI command (no-op by default, override if needed)."""
        pass
    
    def run(self) -> None:
        """Run the CLI command (no-op by default).
        
        For CLI commands, implement execute() directly instead of run().
        """
        self._exit_code = 0
    
    def cleanup(self) -> None:
        """Cleanup after CLI command (no-op by default, override if needed)."""
        pass
    
    def execute(self) -> int:
        """Execute the CLI command lifecycle.
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            # Initialize
            self.init()
            self._initialized = True
            
            # Run (subclasses can override this or implement execute directly)
            self.run()
            
            # Return exit code (default to 0 if not set)
            return self._exit_code if self._exit_code is not None else 0
            
        except KeyboardInterrupt:
            logger.info(f"{self.get_name()} interrupted by user")
            return 130  # Standard exit code for SIGINT
        except SystemExit as e:
            # Allow commands to raise SystemExit with exit code
            return e.code if isinstance(e.code, int) else 1
        except Exception as e:
            logger.error(f"Error in {self.get_name()}: {e}", exc_info=True)
            return 1
        finally:
            # Cleanup
            if self._initialized:
                try:
                    self.cleanup()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}", exc_info=True)


class CommandRunner:
    """Runner for discovering and executing commands using reflection."""
    
    def __init__(self, config: Optional[Any] = None):
        """Initialize the command runner.
        
        Args:
            config: Optional pyiv Config instance for command discovery
        """
        self.config = config
        self._command_cache: Optional[Dict[str, Type[Command]]] = None
    
    def discover_commands(
        self,
        package_path: str,
        pattern: Optional[str] = None,
        recursive: bool = True
    ) -> Dict[str, Type[Command]]:
        """Discover commands in a package using reflection.
        
        Args:
            package_path: Python package path (e.g., "agenticness.commands")
            pattern: Optional name pattern for filtering (e.g., "*Command")
            recursive: Whether to scan submodules recursively
        
        Returns:
            Dictionary mapping command names to command classes
        """
        if self._command_cache is not None:
            return self._command_cache
        
        commands: Dict[str, Type[Command]] = {}
        
        # Use pyiv reflection if config is available and has Command registered
        if self.config is not None:
            try:
                from pyiv.reflection import ReflectionConfig
                if isinstance(self.config, ReflectionConfig):
                    # Try to discover Command implementations
                    try:
                        implementations = self.config.discover_implementations(Command)
                        for name, cmd_class in implementations.items():
                            try:
                                cmd_name = cmd_class.get_name()
                                commands[cmd_name] = cmd_class
                                # Also register aliases
                                for alias in cmd_class.get_aliases():
                                    commands[alias] = cmd_class
                            except Exception as e:
                                # Skip commands that don't implement get_name properly
                                logger.debug(f"Skipping command {name}: {e}")
                                continue
                        if commands:
                            self._command_cache = commands
                            return commands
                    except Exception as e:
                        logger.debug(f"Reflection discovery failed: {e}, falling back to manual discovery")
            except Exception as e:
                logger.debug(f"Config check failed: {e}, falling back to manual discovery")
                # Fall back to manual discovery if reflection fails
                pass
        
        # Manual discovery fallback
        import importlib
        import inspect
        import pkgutil
        
        try:
            package = importlib.import_module(package_path)
            
            # Scan the main module
            for name, obj in inspect.getmembers(package, inspect.isclass):
                if (issubclass(obj, Command) and 
                    obj is not Command and 
                    obj.__module__.startswith(package_path)):
                    try:
                        cmd_name = obj.get_name()
                        commands[cmd_name] = obj
                        for alias in obj.get_aliases():
                            commands[alias] = obj
                    except Exception as e:
                        logger.debug(f"Failed to get name from command {obj.__name__}: {e}")
                        continue
            
            # Recursively scan submodules if requested
            if recursive:
                for importer, modname, ispkg in pkgutil.iter_modules(
                    getattr(package, '__path__', []),
                    package_path + "."
                ):
                    if ispkg:
                        continue
                    
                    try:
                        module = importlib.import_module(modname)
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(obj, Command) and 
                                obj is not Command and 
                                obj.__module__.startswith(package_path)):
                                try:
                                    cmd_name = obj.get_name()
                                    commands[cmd_name] = obj
                                    for alias in obj.get_aliases():
                                        commands[alias] = obj
                                except Exception as e:
                                    logger.debug(f"Failed to get name from command {obj.__name__}: {e}")
                                    continue
                    except Exception as e:
                        logger.debug(f"Failed to import module {modname}: {e}")
                        continue
        
        except Exception as e:
            logger.debug(f"Manual discovery failed: {e}")
            pass
        
        self._command_cache = commands
        return commands
    
    def create_parser(
        self,
        prog: Optional[str] = None,
        description: Optional[str] = None,
        commands: Optional[Dict[str, Type[Command]]] = None
    ) -> argparse.ArgumentParser:
        """Create argument parser with discovered commands.
        
        Args:
            prog: Program name
            description: Program description
            commands: Optional pre-discovered commands dict
        
        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            prog=prog,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        if commands is None:
            # This will be populated by the caller after discovery
            return parser
        
        # Add subparsers for commands
        subparsers = parser.add_subparsers(
            dest="command",
            help="Command to run",
            metavar="COMMAND",
            required=True
        )
        
        # Register all commands
        self._register_commands(subparsers, commands)
        
        return parser
    
    def _register_commands(
        self,
        subparsers: argparse._SubParsersAction,
        commands: Dict[str, Type[Command]],
        parent_path: List[str] = None
    ) -> None:
        """Recursively register commands and their subcommands.
        
        Args:
            subparsers: Subparsers action to add commands to
            commands: Dictionary of command classes to register
            parent_path: Path of parent commands (for hierarchical commands)
        """
        if parent_path is None:
            parent_path = []
        
        for cmd_name, cmd_class in commands.items():
            try:
                description = cmd_class.get_description()
                cmd_parser = subparsers.add_parser(
                    cmd_name,
                    help=description,
                    aliases=cmd_class.get_aliases()
                )
                
                # Add command arguments
                cmd_class.add_args(cmd_parser)
                
                # Check for subcommands
                subcommands = cmd_class.get_subcommands()
                if subcommands:
                    # Create subparsers for subcommands
                    sub_subparsers = cmd_parser.add_subparsers(
                        dest="subcommand",
                        help="Subcommand to run",
                        metavar="SUBCOMMAND",
                        required=True
                    )
                    
                    # Build subcommand dict
                    subcommand_dict: Dict[str, Type[Command]] = {}
                    for subcmd_class in subcommands:
                        subcmd_name = subcmd_class.get_name()
                        subcommand_dict[subcmd_name] = subcmd_class
                        for alias in subcmd_class.get_aliases():
                            subcommand_dict[alias] = subcmd_class
                    
                    # Recursively register subcommands
                    self._register_commands(
                        sub_subparsers,
                        subcommand_dict,
                        parent_path + [cmd_name]
                    )
            except Exception as e:
                # Skip commands that fail to register
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to register command {cmd_name}: {e}")
                continue
    
    def run(
        self,
        package_path: str,
        prog: Optional[str] = None,
        description: Optional[str] = None,
        args: Optional[List[str]] = None
    ) -> int:
        """Discover commands and run the appropriate one.
        
        Args:
            package_path: Python package path to discover commands in
            prog: Program name
            description: Program description
            args: Optional command-line arguments (defaults to sys.argv[1:])
        
        Returns:
            Exit code from command execution
        """
        import sys
        
        # Discover commands
        commands = self.discover_commands(package_path)
        
        if not commands:
            print(f"No commands found in {package_path}", file=sys.stderr)
            return 1
        
        # Create parser
        parser = self.create_parser(prog=prog, description=description)
        
        # Add subparsers
        subparsers = parser.add_subparsers(
            dest="command",
            help="Command to run",
            metavar="COMMAND",
            required=True
        )
        
        # Register commands
        self._register_commands(subparsers, commands)
        
        # Parse arguments
        parsed_args = parser.parse_args(args)
        
        # Find and execute command
        command_class = commands.get(parsed_args.command)
        if not command_class:
            parser.error(f"Unknown command: {parsed_args.command}")
        
        try:
            # Get injector from config if available
            injector = None
            if self.config is not None:
                try:
                    from pyiv import get_injector
                    injector = get_injector(self.config)
                except Exception:
                    pass
            
            command = command_class(parsed_args, injector=injector)
            exit_code = command.execute()
            command.cleanup()
            return exit_code
        except KeyboardInterrupt:
            print("\nInterrupted by user", file=sys.stderr)
            return 130
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

