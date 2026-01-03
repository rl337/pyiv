"""Tests for Console interface and implementations."""

import sys
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from pyiv import Config, get_injector
from pyiv.console import (
    BaseConsole,
    Console,
    CursorMoveEvent,
    EchoChangeEvent,
    FileConsole,
    MemoryConsole,
    MockConsole,
    PTYConsole,
    RealConsole,
    ScreenClearEvent,
)


class TestRealConsole:
    """Tests for RealConsole implementation."""

    def test_write_to_stdout(self):
        """Test writing to stdout."""
        console = RealConsole()
        result = console.write("Hello, World!")
        assert result == 13
        assert console.writable()

    def test_write_to_custom_stream(self):
        """Test writing to a custom stream."""
        stream = StringIO()
        console = RealConsole(stream)
        console.write("Test message")
        console.flush()
        assert stream.getvalue() == "Test message"

    def test_flush(self):
        """Test flushing console."""
        stream = StringIO()
        console = RealConsole(stream)
        console.write("Test")
        console.flush()
        assert stream.getvalue() == "Test"

    def test_writable(self):
        """Test writable check."""
        console = RealConsole()
        assert console.writable()


class TestMemoryConsole:
    """Tests for MemoryConsole implementation."""

    def test_write_and_getvalue(self):
        """Test writing and retrieving value."""
        console = MemoryConsole()
        console.write("Hello, ")
        console.write("World!")
        assert console.getvalue() == "Hello, World!"

    def test_print_to_console(self):
        """Test using console with print()."""
        console = MemoryConsole()
        print("Test message", file=console)
        print("Another line", file=console)
        output = console.getvalue()
        assert "Test message" in output
        assert "Another line" in output

    def test_flush(self):
        """Test flushing (no-op for memory console)."""
        console = MemoryConsole()
        console.write("Test")
        console.flush()  # Should not raise
        assert console.getvalue() == "Test"

    def test_writable(self):
        """Test writable check."""
        console = MemoryConsole()
        assert console.writable()

    def test_seek_and_truncate(self):
        """Test seeking and truncating."""
        console = MemoryConsole()
        console.write("Hello, World!")
        console.seek(0)
        console.truncate(7)
        assert console.getvalue() == "Hello, "

    def test_clear_and_reuse(self):
        """Test clearing and reusing console."""
        console = MemoryConsole()
        print("First output", file=console)
        assert "First output" in console.getvalue()

        # Clear
        console.seek(0)
        console.truncate(0)
        print("Second output", file=console)
        assert "First output" not in console.getvalue()
        assert "Second output" in console.getvalue()

    def test_close(self):
        """Test closing console."""
        console = MemoryConsole()
        console.write("Test")
        # Get value before closing (StringIO can't be read after close)
        value = console.getvalue()
        assert value == "Test"
        console.close()
        # After close, getvalue() will raise ValueError
        with pytest.raises(ValueError):
            console.getvalue()


class TestFileConsole:
    """Tests for FileConsole implementation."""

    def test_write_to_file(self):
        """Test writing to a file."""
        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            console = FileConsole(output_file)
            console.write("Test message")
            console.flush()
            console.close()

            assert output_file.exists()
            assert output_file.read_text() == "Test message"

    def test_print_to_file_console(self):
        """Test using console with print()."""
        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            console = FileConsole(output_file)
            print("Line 1", file=console)
            print("Line 2", file=console)
            console.flush()
            console.close()

            content = output_file.read_text()
            assert "Line 1" in content
            assert "Line 2" in content

    def test_context_manager(self):
        """Test using FileConsole as context manager."""
        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            with FileConsole(output_file) as console:
                console.write("Test message")
                console.flush()

            assert output_file.exists()
            assert output_file.read_text() == "Test message"

    def test_append_mode(self):
        """Test append mode."""
        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            output_file.write_text("Existing content\n")

            console = FileConsole(output_file, mode="a")
            console.write("Appended content")
            console.flush()
            console.close()

            content = output_file.read_text()
            assert "Existing content" in content
            assert "Appended content" in content

    def test_writable(self):
        """Test writable check."""
        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            console = FileConsole(output_file)
            assert console.writable()

    def test_custom_encoding(self):
        """Test custom encoding."""
        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            console = FileConsole(output_file, encoding="utf-8")
            console.write("Test message")
            console.flush()
            console.close()

            assert output_file.read_text(encoding="utf-8") == "Test message"


class TestConsoleInjection:
    """Tests for console dependency injection."""

    def test_inject_real_console(self):
        """Test injecting RealConsole."""

        class Service:
            def __init__(self, console: Console):
                self.console = console

            def greet(self, name: str):
                print(f"Hello, {name}!", file=self.console)

        # Use a custom stream to capture output
        captured = StringIO()

        class MyConfig(Config):
            def configure(self):
                # Register with custom stream for testing
                self.register_instance(Console, RealConsole(captured))

        injector = get_injector(MyConfig)
        service = injector.inject(Service)

        service.greet("Alice")
        service.console.flush()
        output = captured.getvalue()
        assert "Hello, Alice!" in output

    def test_inject_memory_console(self):
        """Test injecting MemoryConsole for testing."""

        class Service:
            def __init__(self, console: Console):
                self.console = console

            def process(self):
                print("Processing...", file=self.console)
                print("Done!", file=self.console)

        class TestConfig(Config):
            def configure(self):
                self.register(Console, MemoryConsole)

        injector = get_injector(TestConfig)
        service = injector.inject(Service)
        service.process()

        # Get console from service and check output
        assert isinstance(service.console, MemoryConsole)
        output = service.console.getvalue()
        assert "Processing..." in output
        assert "Done!" in output

    def test_inject_file_console(self):
        """Test injecting FileConsole for testing."""

        class Service:
            def __init__(self, console: Console):
                self.console = console

            def report(self, message: str):
                print(message, file=self.console)

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "report.txt"

            class TestConfig(Config):
                def configure(self):
                    self.register_instance(Console, FileConsole(output_file))

            injector = get_injector(TestConfig)
            service = injector.inject(Service)
            service.report("Test report")
            service.console.flush()
            service.console.close()

            assert output_file.exists()
            assert "Test report" in output_file.read_text()


class TestBaseConsole:
    """Tests for BaseConsole abstract class."""

    def test_cannot_instantiate_base(self):
        """Test that BaseConsole cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseConsole()  # type: ignore

    def test_custom_console_implementation(self):
        """Test creating a custom console implementation."""

        class CustomConsole(BaseConsole):
            def __init__(self):
                self._output = []

            def write(self, s: str) -> int:
                self._output.append(s)
                return len(s)

            def flush(self) -> None:
                pass

            def writable(self) -> bool:
                return True

            def get_output(self):
                return "".join(self._output)

        console = CustomConsole()
        console.write("Hello")
        console.write(" World")
        assert console.get_output() == "Hello World"
        assert console.writable()


class TestRealConsoleTTY:
    """Tests for RealConsole TTY functionality."""

    def test_is_tty_with_real_stdout(self):
        """Test TTY detection with real stdout."""
        console = RealConsole()
        # May or may not be TTY depending on test environment
        result = console.is_tty()
        assert isinstance(result, bool)

    def test_is_tty_with_custom_stream(self):
        """Test TTY detection with custom stream."""
        stream = StringIO()
        console = RealConsole(stream)
        # StringIO is not a TTY
        assert console.is_tty() == False

    def test_get_size(self):
        """Test getting terminal size."""
        console = RealConsole()
        size = console.get_size()
        assert isinstance(size, tuple)
        assert len(size) == 2
        assert size[0] > 0  # columns
        assert size[1] > 0  # rows

    def test_clear_in_pty(self, pty_context):
        """Test clear screen using PTY context."""
        import os

        master_fd, slave_stream = pty_context
        console = RealConsole(stream=slave_stream)

        console.clear()
        console.flush()

        # Read from master to verify escape sequence
        output = os.read(master_fd, 1024)
        assert b"\033[2J" in output

    def test_move_cursor_in_pty(self, pty_context):
        """Test move cursor using PTY context."""
        import os

        master_fd, slave_stream = pty_context
        console = RealConsole(stream=slave_stream)

        console.move_cursor(10, 5)
        console.flush()

        # Read from master to verify escape sequence
        output = os.read(master_fd, 1024)
        assert b"\033[6;11H" in output  # Row 6 (1-based), Col 11 (1-based)

    def test_set_color_in_pty(self, pty_context):
        """Test set color using PTY context."""
        import os

        master_fd, slave_stream = pty_context
        console = RealConsole(stream=slave_stream)

        console.set_color(fg=31)  # Red
        console.flush()

        # Read from master to verify escape sequence
        output = os.read(master_fd, 1024)
        assert b"\033[31m" in output

    def test_reset_color_in_pty(self, pty_context):
        """Test reset color using PTY context."""
        import os

        master_fd, slave_stream = pty_context
        console = RealConsole(stream=slave_stream)

        console.reset_color()
        console.flush()

        # Read from master to verify escape sequence
        output = os.read(master_fd, 1024)
        assert b"\033[0m" in output


class TestPTYConsole:
    """Tests for PTYConsole implementation."""

    def test_pty_creation(self):
        """Test creating a PTY console."""
        console = PTYConsole()
        assert console.is_tty() == True
        console.close()

    def test_pty_context_manager(self):
        """Test PTY console as context manager."""
        with PTYConsole() as console:
            assert console.is_tty() == True
            assert console.writable()

    def test_pty_escape_sequences(self):
        """Test escape sequences in PTY."""
        with PTYConsole() as console:
            import os

            console.clear()
            console.flush()

            # Read from master to verify
            # ESC can be represented as \x1b or \033
            output = os.read(console.master_fd, 1024)
            # Check for clear screen sequence (ESC[2J)
            assert b"[2J" in output or b"\x1b[2J" in output or b"\033[2J" in output

    def test_pty_size(self):
        """Test getting PTY size."""
        with PTYConsole() as console:
            size = console.get_size()
            assert isinstance(size, tuple)
            assert len(size) == 2
            assert size[0] > 0
            assert size[1] > 0

    def test_pty_write(self):
        """Test writing to PTY."""
        with PTYConsole() as console:
            import os

            console.write("Hello")
            console.flush()

            # Read from master
            output = os.read(console.master_fd, 1024)
            assert b"Hello" in output


class TestMockConsole:
    """Tests for MockConsole state machine."""

    def test_cursor_movement(self):
        """Test cursor movement tracking."""
        console = MockConsole()
        console.move_cursor(10, 5)
        assert console.get_cursor() == (10, 5)

        events = console.get_events()
        assert len(events) == 1
        assert isinstance(events[0], CursorMoveEvent)
        assert events[0].x == 10
        assert events[0].y == 5

    def test_escape_sequence_parsing_clear(self):
        """Test parsing clear screen escape sequence."""
        console = MockConsole()
        console.write("\033[2J")
        assert console.get_cursor() == (0, 0)

        events = console.get_events()
        assert any(e.event_type == "screen_clear" for e in events)

    def test_escape_sequence_parsing_cursor(self):
        """Test parsing cursor position escape sequence."""
        console = MockConsole()
        console.write("\033[5;10H")  # Move to row 5, col 10 (1-based)
        assert console.get_cursor() == (9, 4)  # Converted to 0-based

    def test_escape_sequence_parsing_color(self):
        """Test parsing color escape sequence."""
        console = MockConsole()
        console.write("\033[31m")  # Red foreground
        assert console.get_color() == (31, None)

        console.write("\033[42m")  # Green background
        assert console.get_color() == (31, 42)

        console.write("\033[0m")  # Reset
        assert console.get_color() == (None, None)

    def test_screen_buffer(self):
        """Test screen buffer updates."""
        console = MockConsole(width=80, height=24)
        console.write("Hello")
        console.move_cursor(10, 5)
        console.write("World")

        screen = console.get_screen()
        assert "".join(screen[0][0:5]) == "Hello"
        # move_cursor(10, 5) is 0-based, so row 5 is screen[5]
        assert "".join(screen[5][10:15]) == "World"

    def test_get_screen_line(self):
        """Test getting specific line from screen."""
        console = MockConsole()
        console.write("Line 1")
        console.move_cursor(0, 1)
        console.write("Line 2")

        assert console.get_screen_line(0) == "Line 1" + " " * 74
        assert console.get_screen_line(1) == "Line 2" + " " * 74

    def test_get_screen_char(self):
        """Test getting character at position."""
        console = MockConsole()
        console.write("Hello")

        assert console.get_screen_char(0, 0) == "H"
        assert console.get_screen_char(4, 0) == "o"

    def test_color_state(self):
        """Test color state tracking."""
        console = MockConsole()
        console.set_color(fg=31)  # Red
        assert console.get_color() == (31, None)

        console.set_color(bg=42)  # Green background
        assert console.get_color() == (31, 42)

        console.reset_color()
        assert console.get_color() == (None, None)

    def test_echo_state(self):
        """Test echo state tracking."""
        console = MockConsole()
        assert console.get_echo_enabled() == True

        console.set_echo(False)
        assert console.get_echo_enabled() == False

        events = console.get_events()
        echo_events = [e for e in events if isinstance(e, EchoChangeEvent)]
        assert len(echo_events) == 1
        assert echo_events[0].enabled == False
        assert echo_events[0].previous_state == True

    def test_raw_mode_state(self):
        """Test raw mode state tracking."""
        console = MockConsole()
        assert console.get_raw_mode() == False

        console.set_raw_mode(True)
        assert console.get_raw_mode() == True

    def test_input_simulation(self):
        """Test input simulation."""
        console = MockConsole()
        console.simulate_input("test\n")

        line = console.read_line()
        assert line == "test"

        events = console.get_events()
        input_events = [e for e in events if e.event_type == "input"]
        assert len(input_events) == 1

    def test_password_prompt(self):
        """Test password prompt with echo disabled."""
        console = MockConsole()
        console.simulate_input("secret123\n")

        password = console.read_password("Password: ")
        assert password == "secret123"
        assert console.get_echo_enabled() == True  # Restored

        # Check events
        events = console.get_events()
        echo_events = [e for e in events if isinstance(e, EchoChangeEvent)]
        assert len(echo_events) >= 2  # Disabled and enabled

    def test_clear_state(self):
        """Test clearing state."""
        console = MockConsole()
        console.write("Hello")
        console.move_cursor(10, 5)
        console.set_color(fg=31)

        console.clear_state()

        assert console.get_cursor() == (0, 0)
        assert console.get_color() == (None, None)
        assert len(console.get_events()) == 0

    def test_write_with_newline(self):
        """Test writing with newline characters."""
        console = MockConsole()
        console.write("Line 1\nLine 2")

        screen = console.get_screen()
        assert "".join(screen[0][0:6]) == "Line 1"
        assert "".join(screen[1][0:6]) == "Line 2"

    def test_write_with_tab(self):
        """Test writing with tab characters."""
        console = MockConsole()
        console.write("A\tB")

        # Tab moves to next 8-column boundary
        # After "A" (pos 1), tab moves to 8, then "B" moves to 9
        assert console.get_cursor()[0] == 9

    def test_write_with_backspace(self):
        """Test writing with backspace."""
        console = MockConsole()
        console.write("Hello\b\b")

        assert console.get_cursor()[0] == 3  # Moved back 2 positions

    def test_multiple_events(self):
        """Test tracking multiple events."""
        console = MockConsole()
        console.clear()
        console.move_cursor(10, 5)
        console.set_color(fg=31)
        console.write("Hello")
        console.reset_color()

        events = console.get_events()
        assert len(events) == 5
        assert isinstance(events[0], ScreenClearEvent)
        assert isinstance(events[1], CursorMoveEvent)
        assert events[1].x == 10
        assert events[1].y == 5
