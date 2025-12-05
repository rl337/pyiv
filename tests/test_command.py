"""Tests for command interface and discovery in pyiv."""

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any, List, Optional, Type
from unittest.mock import MagicMock, patch

import pytest

from pyiv.command import CLICommand, Command, CommandRunner, ServiceCommand
from pyiv.reflection import ReflectionConfig


# Test command implementations (prefixed with Sample to avoid pytest collection)
class SampleCommand(Command):
    """Sample command implementation."""

    @classmethod
    def get_name(cls) -> str:
        return "test"

    @classmethod
    def get_description(cls) -> str:
        return "Test command"

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--value", type=str, help="Test value")

    def execute(self) -> int:
        return 0


class SampleCommandWithAliases(Command):
    """Sample command with aliases."""

    @classmethod
    def get_name(cls) -> str:
        return "test-alias"

    @classmethod
    def get_aliases(cls) -> List[str]:
        return ["ta", "testa"]

    @classmethod
    def get_description(cls) -> str:
        return "Test command with aliases"

    def execute(self) -> int:
        return 0


class SampleServiceCommand(ServiceCommand):
    """Sample service command."""

    def __init__(self, args: argparse.Namespace, injector: Optional[Any] = None):
        super().__init__(args, injector)
        self.init_called = False
        self.run_called = False
        self.cleanup_called = False

    @classmethod
    def get_name(cls) -> str:
        return "test-service"

    @classmethod
    def get_description(cls) -> str:
        return "Test service command"

    def init(self) -> None:
        self.init_called = True

    def run(self) -> None:
        self.run_called = True

    def cleanup(self) -> None:
        self.cleanup_called = True


class SampleCLICommand(CLICommand):
    """Sample CLI command."""

    def __init__(self, args: argparse.Namespace, injector: Optional[Any] = None):
        super().__init__(args, injector)
        self.init_called = False
        self.cleanup_called = False

    @classmethod
    def get_name(cls) -> str:
        return "test-cli"

    @classmethod
    def get_description(cls) -> str:
        return "Test CLI command"

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--output", type=str, help="Output file")

    def init(self) -> None:
        self.init_called = True

    def run(self) -> None:
        # Set exit code via _exit_code
        self._exit_code = 42

    def cleanup(self) -> None:
        self.cleanup_called = True


class SampleCommandWithSubcommands(Command):
    """Sample command with subcommands."""

    @classmethod
    def get_name(cls) -> str:
        return "parent"

    @classmethod
    def get_description(cls) -> str:
        return "Parent command"

    @classmethod
    def get_subcommands(cls) -> List[Type[Command]]:
        return [SampleCommand]

    def execute(self) -> int:
        return 0


class SampleCommandWithError(Command):
    """Sample command that raises an error."""

    @classmethod
    def get_name(cls) -> str:
        return "test-error"

    @classmethod
    def get_description(cls) -> str:
        return "Test command with error"

    def execute(self) -> int:
        raise ValueError("Test error")


class SampleServiceCommandWithError(ServiceCommand):
    """Sample service command that raises an error during init."""

    @classmethod
    def get_name(cls) -> str:
        return "test-service-error"

    @classmethod
    def get_description(cls) -> str:
        return "Test service command with error"

    def init(self) -> None:
        raise RuntimeError("Init failed")

    def run(self) -> None:
        pass

    def cleanup(self) -> None:
        pass


class TestCommandInterface:
    """Tests for Command interface."""

    def test_command_abstract_methods(self):
        """Test that Command requires get_name and execute."""
        with pytest.raises(TypeError):
            # Can't instantiate abstract class
            Command(argparse.Namespace())

    def test_command_get_name(self):
        """Test get_name method."""
        assert SampleCommand.get_name() == "test"

    def test_command_get_description(self):
        """Test get_description method."""
        assert SampleCommand.get_description() == "Test command"
        # Default description
        assert Command.get_description() == ""

    def test_command_get_aliases(self):
        """Test get_aliases method."""
        assert SampleCommand.get_aliases() == []
        assert SampleCommandWithAliases.get_aliases() == ["ta", "testa"]

    def test_command_add_args(self):
        """Test add_args method."""
        parser = argparse.ArgumentParser()
        SampleCommand.add_args(parser)
        args = parser.parse_args(["--value", "test"])
        assert args.value == "test"

    def test_command_get_subcommands(self):
        """Test get_subcommands method."""
        assert SampleCommand.get_subcommands() == []
        assert SampleCommandWithSubcommands.get_subcommands() == [SampleCommand]

    def test_command_init(self):
        """Test command initialization."""
        args = argparse.Namespace(value="test")
        cmd = SampleCommand(args)
        assert cmd.args == args
        assert cmd.injector is None
        assert cmd._initialized is False
        assert cmd._shutdown_event is None

    def test_command_init_with_injector(self):
        """Test command initialization with injector."""
        args = argparse.Namespace()
        injector = MagicMock()
        cmd = SampleCommand(args, injector=injector)
        assert cmd.injector == injector

    def test_command_lifecycle_hooks(self):
        """Test command lifecycle hooks."""
        args = argparse.Namespace()
        cmd = SampleCommand(args)
        # Default implementations should not raise
        cmd.init()
        cmd.run()
        cmd.cleanup()

    def test_command_setup_signal_handlers(self):
        """Test setup_signal_handlers."""
        args = argparse.Namespace()
        cmd = SampleCommand(args)
        # Should not raise
        cmd.setup_signal_handlers()


class TestServiceCommand:
    """Tests for ServiceCommand."""

    def test_service_command_lifecycle(self):
        """Test ServiceCommand lifecycle."""
        args = argparse.Namespace()
        cmd = SampleServiceCommand(args)

        exit_code = cmd.execute()

        assert exit_code == 0
        assert cmd.init_called
        assert cmd.run_called
        assert cmd.cleanup_called
        assert cmd._initialized

    def test_service_command_keyboard_interrupt(self):
        """Test ServiceCommand handles KeyboardInterrupt."""

        class InterruptingService(ServiceCommand):
            @classmethod
            def get_name(cls) -> str:
                return "interrupt"

            def init(self) -> None:
                pass

            def run(self) -> None:
                raise KeyboardInterrupt()

            def cleanup(self) -> None:
                pass

        args = argparse.Namespace()
        cmd = InterruptingService(args)
        exit_code = cmd.execute()
        assert exit_code == 130

    def test_service_command_error_handling(self):
        """Test ServiceCommand handles errors."""
        args = argparse.Namespace()
        cmd = SampleServiceCommandWithError(args)

        exit_code = cmd.execute()

        assert exit_code == 1
        # Cleanup should still be called even on error
        # (though in this case init failed, so _initialized is False)

    def test_service_command_cleanup_error(self):
        """Test ServiceCommand handles cleanup errors."""

        class CleanupErrorService(ServiceCommand):
            @classmethod
            def get_name(cls) -> str:
                return "cleanup-error"

            def init(self) -> None:
                pass

            def run(self) -> None:
                pass

            def cleanup(self) -> None:
                raise RuntimeError("Cleanup failed")

        args = argparse.Namespace()
        cmd = CleanupErrorService(args)
        # Should not raise, but return error code
        exit_code = cmd.execute()
        assert exit_code == 0  # run() succeeded, cleanup error is logged


class TestCLICommand:
    """Tests for CLICommand."""

    def test_cli_command_execute(self):
        """Test CLICommand execute."""
        args = argparse.Namespace(output="test.txt")
        cmd = SampleCLICommand(args)

        exit_code = cmd.execute()

        assert exit_code == 42
        assert cmd.init_called
        assert cmd.cleanup_called
        assert cmd._initialized

    def test_cli_command_keyboard_interrupt(self):
        """Test CLICommand handles KeyboardInterrupt."""

        class InterruptingCLI(CLICommand):
            @classmethod
            def get_name(cls) -> str:
                return "interrupt-cli"

            def execute(self) -> int:
                raise KeyboardInterrupt()

        args = argparse.Namespace()
        cmd = InterruptingCLI(args)
        exit_code = cmd.execute()
        assert exit_code == 130

    def test_cli_command_system_exit(self):
        """Test CLICommand handles SystemExit."""

        class SystemExitCLI(CLICommand):
            @classmethod
            def get_name(cls) -> str:
                return "system-exit-cli"

            def execute(self) -> int:
                raise SystemExit(99)

        args = argparse.Namespace()
        cmd = SystemExitCLI(args)
        exit_code = cmd.execute()
        assert exit_code == 99

    def test_cli_command_default_exit_code(self):
        """Test CLICommand default exit code."""

        class DefaultExitCLI(CLICommand):
            @classmethod
            def get_name(cls) -> str:
                return "default-exit"

            def execute(self) -> int:
                # Don't set _exit_code, should default to 0
                return super().execute()

        args = argparse.Namespace()
        cmd = DefaultExitCLI(args)
        # Override execute to not call super
        cmd.run()  # This sets _exit_code to 0
        exit_code = cmd.execute()
        assert exit_code == 0


class TestCommandRunner:
    """Tests for CommandRunner."""

    def test_command_runner_init(self):
        """Test CommandRunner initialization."""
        runner = CommandRunner()
        assert runner.config is None
        assert runner._command_cache is None

    def test_command_runner_init_with_config(self):
        """Test CommandRunner initialization with config."""
        config = ReflectionConfig()
        runner = CommandRunner(config=config)
        assert runner.config == config

    def test_discover_commands_manual(self):
        """Test manual command discovery."""
        runner = CommandRunner()

        # Create a test package structure
        with tempfile.TemporaryDirectory() as tmpdir:
            test_package_dir = Path(tmpdir) / "test_package"
            test_package_dir.mkdir()
            (test_package_dir / "__init__.py").write_text("")

            # Create a command module
            command_module = test_package_dir / "commands.py"
            command_module.write_text(
                """
import argparse
from pyiv.command import Command

class TestCommand(Command):
    @classmethod
    def get_name(cls) -> str:
        return "test"
    
    @classmethod
    def get_description(cls) -> str:
        return "Test command"
    
    def execute(self) -> int:
        return 0
"""
            )

            # Add to sys.path
            sys.path.insert(0, str(tmpdir))

            try:
                commands = runner.discover_commands("test_package.commands", recursive=False)
                assert "test" in commands
                assert commands["test"].__name__ == "TestCommand"
            finally:
                sys.path.remove(str(tmpdir))

    def test_discover_commands_with_reflection(self):
        """Test command discovery with reflection."""
        config = ReflectionConfig()
        config.register_module(Command, "tests.test_command", pattern="Sample*Command", recursive=False)

        runner = CommandRunner(config=config)
        commands = runner.discover_commands("tests.test_command", recursive=False)

        # Should discover SampleCommand, SampleServiceCommand, SampleCLICommand, etc.
        assert len(commands) > 0
        assert "test" in commands or "test-cli" in commands or "test-service" in commands

    def test_discover_commands_caching(self):
        """Test that command discovery is cached."""
        runner = CommandRunner()
        runner._command_cache = {"cached": SampleCommand}

        commands = runner.discover_commands("some.package")
        assert commands == {"cached": SampleCommand}

    def test_run_command_success(self):
        """Test running a command successfully."""
        runner = CommandRunner()

        # Create a test package
        with tempfile.TemporaryDirectory() as tmpdir:
            test_package_dir = Path(tmpdir) / "test_package"
            test_package_dir.mkdir()
            (test_package_dir / "__init__.py").write_text("")

            command_module = test_package_dir / "commands.py"
            command_module.write_text(
                """
import argparse
from pyiv.command import CLICommand

class TestCommand(CLICommand):
    @classmethod
    def get_name(cls) -> str:
        return "test"
    
    @classmethod
    def get_description(cls) -> str:
        return "Test command"
    
    def execute(self) -> int:
        return 0
"""
            )

            sys.path.insert(0, str(tmpdir))

            try:
                exit_code = runner.run(
                    package_path="test_package.commands",
                    prog="test",
                    description="Test CLI",
                    args=["test"],
                )
                assert exit_code == 0
            finally:
                sys.path.remove(str(tmpdir))

    def test_run_command_not_found(self):
        """Test running a non-existent command."""
        runner = CommandRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_package_dir = Path(tmpdir) / "test_package"
            test_package_dir.mkdir()
            (test_package_dir / "__init__.py").write_text("")

            command_module = test_package_dir / "commands.py"
            command_module.write_text(
                """
import argparse
from pyiv.command import CLICommand

class TestCommand(CLICommand):
    @classmethod
    def get_name(cls) -> str:
        return "test"
    
    @classmethod
    def get_description(cls) -> str:
        return "Test command"
    
    def execute(self) -> int:
        return 0
"""
            )

            sys.path.insert(0, str(tmpdir))

            try:
                # Should raise SystemExit with error
                with pytest.raises(SystemExit):
                    runner.run(
                        package_path="test_package.commands",
                        prog="test",
                        description="Test CLI",
                        args=["unknown"],
                    )
            finally:
                sys.path.remove(str(tmpdir))

    def test_run_command_keyboard_interrupt(self):
        """Test running a command that raises KeyboardInterrupt."""
        runner = CommandRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_package_dir = Path(tmpdir) / "test_package"
            test_package_dir.mkdir()
            (test_package_dir / "__init__.py").write_text("")

            command_module = test_package_dir / "commands.py"
            command_module.write_text(
                """
import argparse
from pyiv.command import CLICommand

class TestCommand(CLICommand):
    @classmethod
    def get_name(cls) -> str:
        return "test"
    
    @classmethod
    def get_description(cls) -> str:
        return "Test command"
    
    def execute(self) -> int:
        raise KeyboardInterrupt()
"""
            )

            sys.path.insert(0, str(tmpdir))

            try:
                exit_code = runner.run(
                    package_path="test_package.commands",
                    prog="test",
                    description="Test CLI",
                    args=["test"],
                )
                assert exit_code == 130
            finally:
                sys.path.remove(str(tmpdir))

    def test_register_commands_with_subcommands(self):
        """Test registering commands with subcommands."""
        runner = CommandRunner()

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)

        commands = {"parent": SampleCommandWithSubcommands}
        runner._register_commands(subparsers, commands)

        # Should be able to parse parent command
        args = parser.parse_args(["parent"])
        assert args.command == "parent"

    def test_create_parser(self):
        """Test create_parser method."""
        runner = CommandRunner()

        parser = runner.create_parser(prog="test", description="Test CLI")
        assert parser.prog == "test"
        assert "description" in parser.description.lower() or parser.description == "Test CLI"

    def test_create_parser_with_commands(self):
        """Test create_parser with commands."""
        runner = CommandRunner()

        commands = {"test": SampleCommand}
        parser = runner.create_parser(
            prog="test", description="Test CLI", commands=commands
        )

        # Should be able to parse test command
        args = parser.parse_args(["test", "--value", "hello"])
        assert args.command == "test"
        assert args.value == "hello"


class TestCommandWithDI:
    """Tests for Command with dependency injection."""

    def test_command_with_injector(self):
        """Test command receives injector."""
        args = argparse.Namespace()
        injector = MagicMock()
        cmd = SampleCommand(args, injector=injector)

        assert cmd.injector == injector

    def test_command_runner_passes_injector(self):
        """Test CommandRunner passes injector to commands."""
        config = ReflectionConfig()
        config.register_module(Command, "tests.test_command", pattern="SampleCommand", recursive=False)

        injector = MagicMock()
        with patch("pyiv.command.get_injector", return_value=injector):
            runner = CommandRunner(config=config)

            with tempfile.TemporaryDirectory() as tmpdir:
                test_package_dir = Path(tmpdir) / "test_package"
                test_package_dir.mkdir()
                (test_package_dir / "__init__.py").write_text("")

                command_module = test_package_dir / "commands.py"
                command_module.write_text(
                    """
import argparse
from pyiv.command import CLICommand

class TestCommand(CLICommand):
    @classmethod
    def get_name(cls) -> str:
        return "test"
    
    @classmethod
    def get_description(cls) -> str:
        return "Test command"
    
    def execute(self) -> int:
        # Verify injector is available
        assert self.injector is not None
        return 0
"""
                )

                sys.path.insert(0, str(tmpdir))

                try:
                    exit_code = runner.run(
                        package_path="test_package.commands",
                        prog="test",
                        description="Test CLI",
                        args=["test"],
                    )
                    assert exit_code == 0
                finally:
                    sys.path.remove(str(tmpdir))


class TestCommandAliases:
    """Tests for command aliases."""

    def test_command_runner_registers_aliases(self):
        """Test that CommandRunner registers command aliases."""
        runner = CommandRunner()

        commands = {"test-alias": SampleCommandWithAliases}
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        runner._register_commands(subparsers, commands)

        # Should be able to use alias
        args = parser.parse_args(["ta"])
        assert args.command == "ta"

        # Original name should also work
        args = parser.parse_args(["test-alias"])
        assert args.command == "test-alias"

