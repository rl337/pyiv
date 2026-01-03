"""Console output abstraction for dependency injection.

This module provides a file-like interface for console output, allowing
print() statements to be replaced with injectable console objects. This
enables testing by capturing console output without actually printing
to stdout.

**What Problem Does This Solve?**

Console output solves the "print() testing" problem:
- **Testability**: Capture print() output in tests without mocking sys.stdout
- **Flexibility**: Redirect console output to files, memory, or custom handlers
- **Dependency Injection**: Make console output injectable like other dependencies
- **Separation of Concerns**: Distinguish user-facing output (console) from logging
- **Test Isolation**: Each test can have its own console instance

**Real-World Use Cases:**
- **CLI Applications**: Capture command output for testing
- **Interactive Programs**: Test user prompts and responses
- **Progress Indicators**: Test progress bars and status messages
- **Error Messages**: Capture and verify error output
- **Report Generation**: Redirect reports to files or memory

Architecture:
    - Console: Protocol defining file-like console interface
    - RealConsole: Production implementation using sys.stdout
    - MemoryConsole: Test implementation with in-memory storage
    - FileConsole: Test implementation writing to a file

Usage Examples:

    Basic Console Usage:
        >>> from pyiv.console import RealConsole, MemoryConsole
        >>> from pyiv import Config, get_injector
        >>>
        >>> class Service:
        ...     def __init__(self, console: Console):
        ...         self.console = console
        ...
        ...     def greet(self, name: str):
        ...         print(f"Hello, {name}!", file=self.console)
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Console, RealConsole)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> service = injector.inject(Service)
        >>> service.greet("Alice")  # Prints to stdout

    Testing with MemoryConsole:
        >>> from pyiv.console import MemoryConsole
        >>> from io import StringIO
        >>>
        >>> console = MemoryConsole()
        >>> print("Hello, World!", file=console)
        >>> print("Test output", file=console)
        >>>
        >>> # Get captured output
        >>> output = console.getvalue()
        >>> assert "Hello, World!" in output
        >>> assert "Test output" in output

    Testing with FileConsole:
        >>> from pyiv.console import FileConsole
        >>> from pathlib import Path
        >>>
        >>> output_file = Path("/tmp/test_output.txt")
        >>> console = FileConsole(output_file)
        >>> print("Test message", file=console)
        >>> console.flush()
        >>>
        >>> # Read back the output
        >>> content = output_file.read_text()
        >>> assert "Test message" in content
"""

import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import Dict, List, Optional, Protocol, TextIO, Tuple, Union

# ANSI Escape Sequence Constants
ESC = "\033"
CLEAR_SCREEN = "\033[2J"
CLEAR_LINE = "\033[2K"
CLEAR_TO_END_OF_LINE = "\033[0K"
CURSOR_HOME = "\033[H"
RESET_COLOR = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# ANSI Color Codes
BLACK = 30
RED = 31
GREEN = 32
YELLOW = 33
BLUE = 34
MAGENTA = 35
CYAN = 36
WHITE = 37
DEFAULT = 39

# ANSI Style Codes
BOLD = 1
DIM = 2
ITALIC = 3
UNDERLINE = 4
STRIKETHROUGH = 9


@dataclass
class TerminalEvent:
    """Base class for terminal events."""

    timestamp: float
    event_type: str


@dataclass
class CursorMoveEvent(TerminalEvent):
    """Event for cursor movement."""

    x: int
    y: int


@dataclass
class ColorChangeEvent(TerminalEvent):
    """Event for color changes."""

    fg: Optional[int]
    bg: Optional[int]


@dataclass
class ScreenClearEvent(TerminalEvent):
    """Event for screen clearing."""

    pass


@dataclass
class WriteEvent(TerminalEvent):
    """Event for text writes."""

    text: str


@dataclass
class EchoChangeEvent(TerminalEvent):
    """Event for echo state changes."""

    enabled: bool
    previous_state: bool


@dataclass
class RawModeChangeEvent(TerminalEvent):
    """Event for raw mode changes."""

    enabled: bool
    previous_state: bool


@dataclass
class InputEvent(TerminalEvent):
    """Event for input operations."""

    text: str


class Console(Protocol):
    """Protocol for console output implementations.

    Console provides a file-like interface for output, allowing print()
    statements to use dependency injection. This enables testing by
    capturing output without actually printing to stdout.

    Console implementations should be file-like objects that support
    the standard file interface (write, flush, etc.) used by print().

    Example:
        >>> from pyiv.console import RealConsole
        >>>
        >>> console = RealConsole()
        >>> print("Hello, World!", file=console)
        >>> console.flush()
    """

    def write(self, s: str) -> int:
        """Write string to console.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        ...

    def flush(self) -> None:
        """Flush any buffered output.

        Ensures all written data is actually output.
        """
        ...

    def writable(self) -> bool:
        """Check if console is writable.

        Returns:
            True if console supports writing
        """
        ...


class BaseConsole(ABC):
    """Abstract base class for console implementations.

    Provides a concrete base class for console implementations.
    Subclasses should implement the file-like interface methods.

    Example:
        >>> from pyiv.console import BaseConsole
        >>>
        >>> class CustomConsole(BaseConsole):
        ...     def write(self, s: str) -> int:
        ...         # Custom write logic
        ...         return len(s)
        ...
        ...     def flush(self) -> None:
        ...         pass
        ...
        ...     def writable(self) -> bool:
        ...         return True
    """

    @abstractmethod
    def write(self, s: str) -> int:
        """Write string to console.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered output."""
        pass

    @abstractmethod
    def writable(self) -> bool:
        """Check if console is writable.

        Returns:
            True if console supports writing
        """
        pass


class Terminal(Protocol):
    """Protocol for terminal implementations extending Console.

    Terminal provides TTY-specific functionality including cursor control,
    colors, screen clearing, and input control. This enables spinners,
    animations, password prompts, progress bars, and interactive CLI features.

    Example:
        >>> from pyiv.console import RealConsole
        >>>
        >>> terminal = RealConsole()
        >>> if terminal.is_tty():
        ...     terminal.clear()
        ...     terminal.move_cursor(10, 5)
        ...     terminal.set_color(fg=31)  # Red
        ...     terminal.write("Hello")
        ...     terminal.reset_color()
    """

    # Console interface (inherited)
    def write(self, s: str) -> int:
        """Write string to console."""
        ...

    def flush(self) -> None:
        """Flush any buffered output."""
        ...

    def writable(self) -> bool:
        """Check if console is writable."""
        ...

    # TTY Queries
    def is_tty(self) -> bool:
        """Check if output is a real terminal.

        Returns:
            True if output is connected to a TTY
        """
        ...

    def get_size(self) -> Tuple[int, int]:
        """Get terminal size.

        Returns:
            Tuple of (columns, rows)
        """
        ...

    def get_cursor_position(self) -> Optional[Tuple[int, int]]:
        """Get current cursor position.

        Returns:
            Tuple of (x, y) or None if not available
        """
        ...

    # Output Control
    def clear(self) -> None:
        """Clear the entire screen."""
        ...

    def clear_line(self) -> None:
        """Clear the current line."""
        ...

    def clear_to_end_of_line(self) -> None:
        """Clear from cursor to end of line."""
        ...

    def move_cursor(self, x: int, y: int) -> None:
        """Move cursor to position.

        Args:
            x: Column (0-based)
            y: Row (0-based)
        """
        ...

    def move_cursor_home(self) -> None:
        """Move cursor to home position (0, 0)."""
        ...

    def move_cursor_up(self, n: int = 1) -> None:
        """Move cursor up n lines."""
        ...

    def move_cursor_down(self, n: int = 1) -> None:
        """Move cursor down n lines."""
        ...

    def move_cursor_left(self, n: int = 1) -> None:
        """Move cursor left n columns."""
        ...

    def move_cursor_right(self, n: int = 1) -> None:
        """Move cursor right n columns."""
        ...

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        ...

    def show_cursor(self) -> None:
        """Show the cursor."""
        ...

    def save_cursor(self) -> None:
        """Save current cursor position."""
        ...

    def restore_cursor(self) -> None:
        """Restore saved cursor position."""
        ...

    # Color and Style
    def set_color(self, fg: Optional[int] = None, bg: Optional[int] = None) -> None:
        """Set foreground and/or background color.

        Args:
            fg: Foreground color code (30-37 for basic, 30-37,90-97 for bright)
            bg: Background color code (40-47 for basic, 100-107 for bright)
        """
        ...

    def reset_color(self) -> None:
        """Reset colors to default."""
        ...

    def bold(self, enabled: bool = True) -> None:
        """Enable or disable bold text."""
        ...

    def underline(self, enabled: bool = True) -> None:
        """Enable or disable underline."""
        ...

    # Input Control
    def set_echo(self, enabled: bool) -> None:
        """Turn echo on/off for password prompts.

        Args:
            enabled: True to enable echo, False to disable
        """
        ...

    def set_raw_mode(self, enabled: bool) -> None:
        """Enable/disable raw mode for character-by-character input.

        Args:
            enabled: True for raw mode, False for cooked mode
        """
        ...

    def read_char(self) -> Optional[str]:
        """Read a single character (requires raw mode).

        Returns:
            Character string or None if no input available
        """
        ...

    def read_line(self) -> str:
        """Read a line of input.

        Returns:
            Line of text (without newline)
        """
        ...

    def read_password(self, prompt: str = "") -> str:
        """Read password with echo disabled.

        Args:
            prompt: Optional prompt to display

        Returns:
            Password string
        """
        ...

    # State Queries (for MockConsole)
    def get_cursor(self) -> Tuple[int, int]:
        """Get current cursor position (for state inspection).

        Returns:
            Tuple of (x, y)
        """
        ...

    def get_screen(self) -> List[List[str]]:
        """Get screen buffer (for state inspection).

        Returns:
            2D list of screen contents
        """
        ...

    def get_color(self) -> Tuple[Optional[int], Optional[int]]:
        """Get current color state (for state inspection).

        Returns:
            Tuple of (fg, bg)
        """
        ...

    def get_echo_enabled(self) -> bool:
        """Get echo state (for state inspection).

        Returns:
            True if echo is enabled
        """
        ...

    def get_raw_mode(self) -> bool:
        """Get raw mode state (for state inspection).

        Returns:
            True if raw mode is enabled
        """
        ...

    def get_events(self) -> List[TerminalEvent]:
        """Get event history (for state inspection).

        Returns:
            List of terminal events
        """
        ...


class RealConsole(BaseConsole):
    """Production console implementation using sys.stdout.

    This console wraps sys.stdout, providing the standard console output
    behavior and TTY-specific functionality. Use this in production code
    for normal console output and terminal features like spinners, animations,
    and password prompts.

    Example:
        >>> from pyiv.console import RealConsole
        >>> from pyiv import Config, get_injector
        >>>
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(Console, RealConsole)
        >>>
        >>> injector = get_injector(MyConfig)
        >>> console = injector.inject(Console)
        >>> print("Hello, World!", file=console)  # Prints to stdout
        >>>
        >>> # TTY features
        >>> if console.is_tty():
        ...     console.clear()
        ...     console.move_cursor(10, 5)
        ...     console.set_color(fg=31)  # Red
        ...     console.write("Hello")
        ...     console.reset_color()
    """

    def __init__(self, stream: Optional[TextIO] = None, stdin: Optional[TextIO] = None):
        """Initialize console with streams.

        Args:
            stream: TextIO stream to use for output (defaults to sys.stdout)
            stdin: TextIO stream to use for input (defaults to sys.stdin)
        """
        self._stream: TextIO = stream if stream is not None else sys.stdout
        self._stdin: TextIO = stdin if stdin is not None else sys.stdin
        self._saved_termios_attrs: Optional[List] = None

    def write(self, s: str) -> int:
        """Write string to stdout.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        return self._stream.write(s)

    def flush(self) -> None:
        """Flush stdout buffer."""
        self._stream.flush()

    def writable(self) -> bool:
        """Check if stdout is writable.

        Returns:
            True if stdout is writable
        """
        return self._stream.writable()

    # TTY Queries
    def is_tty(self) -> bool:
        """Check if stdout is a real terminal.

        Returns:
            True if stdout is connected to a TTY
        """
        return self._stream.isatty() if hasattr(self._stream, "isatty") else False

    def get_size(self) -> Tuple[int, int]:
        """Get terminal size.

        Returns:
            Tuple of (columns, rows)
        """
        try:
            size = os.get_terminal_size()
            return (size.columns, size.lines)
        except OSError:
            return (80, 24)  # Default

    def get_cursor_position(self) -> Optional[Tuple[int, int]]:
        """Get current cursor position.

        Note: This requires reading a response from the terminal, which may
        not be available in all contexts.

        Returns:
            Tuple of (x, y) or None if not available
        """
        # Cursor position query requires escape sequence and reading response
        # This is complex and may not work in all contexts
        # For now, return None - can be enhanced later
        return None

    # Output Control
    def clear(self) -> None:
        """Clear the entire screen."""
        if self.is_tty():
            self.write(CLEAR_SCREEN)
            self.flush()

    def clear_line(self) -> None:
        """Clear the current line."""
        if self.is_tty():
            self.write(CLEAR_LINE)
            self.flush()

    def clear_to_end_of_line(self) -> None:
        """Clear from cursor to end of line."""
        if self.is_tty():
            self.write(CLEAR_TO_END_OF_LINE)
            self.flush()

    def move_cursor(self, x: int, y: int) -> None:
        """Move cursor to position.

        Args:
            x: Column (0-based, but ANSI uses 1-based)
            y: Row (0-based, but ANSI uses 1-based)
        """
        if self.is_tty():
            # ANSI uses 1-based coordinates
            self.write(f"\033[{y + 1};{x + 1}H")
            self.flush()

    def move_cursor_home(self) -> None:
        """Move cursor to home position (0, 0)."""
        if self.is_tty():
            self.write(CURSOR_HOME)
            self.flush()

    def move_cursor_up(self, n: int = 1) -> None:
        """Move cursor up n lines."""
        if self.is_tty():
            self.write(f"\033[{n}A")
            self.flush()

    def move_cursor_down(self, n: int = 1) -> None:
        """Move cursor down n lines."""
        if self.is_tty():
            self.write(f"\033[{n}B")
            self.flush()

    def move_cursor_left(self, n: int = 1) -> None:
        """Move cursor left n columns."""
        if self.is_tty():
            self.write(f"\033[{n}D")
            self.flush()

    def move_cursor_right(self, n: int = 1) -> None:
        """Move cursor right n columns."""
        if self.is_tty():
            self.write(f"\033[{n}C")
            self.flush()

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        if self.is_tty():
            self.write(HIDE_CURSOR)
            self.flush()

    def show_cursor(self) -> None:
        """Show the cursor."""
        if self.is_tty():
            self.write(SHOW_CURSOR)
            self.flush()

    def save_cursor(self) -> None:
        """Save current cursor position."""
        if self.is_tty():
            self.write("\033[s")
            self.flush()

    def restore_cursor(self) -> None:
        """Restore saved cursor position."""
        if self.is_tty():
            self.write("\033[u")
            self.flush()

    # Color and Style
    def set_color(self, fg: Optional[int] = None, bg: Optional[int] = None) -> None:
        """Set foreground and/or background color.

        Args:
            fg: Foreground color code (30-37 for basic, 90-97 for bright)
            bg: Background color code (40-47 for basic, 100-107 for bright)
        """
        if self.is_tty():
            codes = []
            if fg is not None:
                codes.append(str(fg))
            if bg is not None:
                codes.append(str(bg))
            if codes:
                self.write(f"\033[{';'.join(codes)}m")
                self.flush()

    def reset_color(self) -> None:
        """Reset colors to default."""
        if self.is_tty():
            self.write(RESET_COLOR)
            self.flush()

    def bold(self, enabled: bool = True) -> None:
        """Enable or disable bold text.

        Args:
            enabled: True to enable bold, False to disable
        """
        if self.is_tty():
            if enabled:
                self.write(f"\033[{BOLD}m")
            else:
                self.write("\033[22m")  # Reset bold
            self.flush()

    def underline(self, enabled: bool = True) -> None:
        """Enable or disable underline.

        Args:
            enabled: True to enable underline, False to disable
        """
        if self.is_tty():
            if enabled:
                self.write(f"\033[{UNDERLINE}m")
            else:
                self.write("\033[24m")  # Reset underline
            self.flush()

    # Input Control
    def set_echo(self, enabled: bool) -> None:
        """Turn echo on/off for password prompts.

        Args:
            enabled: True to enable echo, False to disable
        """
        if not self.is_tty():
            return

        try:
            import termios

            fd = self._stdin.fileno() if hasattr(self._stdin, "fileno") else None
            if fd is None:
                return

            if self._saved_termios_attrs is None:
                self._saved_termios_attrs = termios.tcgetattr(fd)

            attrs = termios.tcgetattr(fd)
            if enabled:
                attrs[3] |= termios.ECHO
            else:
                attrs[3] &= ~termios.ECHO

            termios.tcsetattr(fd, termios.TCSANOW, attrs)
        except (ImportError, OSError, AttributeError):
            # termios not available or not a TTY
            pass

    def set_raw_mode(self, enabled: bool) -> None:
        """Enable/disable raw mode for character-by-character input.

        Args:
            enabled: True for raw mode, False for cooked mode
        """
        if not self.is_tty():
            return

        try:
            import termios
            import tty

            fd = self._stdin.fileno() if hasattr(self._stdin, "fileno") else None
            if fd is None:
                return

            if enabled:
                if self._saved_termios_attrs is None:
                    self._saved_termios_attrs = termios.tcgetattr(fd)
                tty.setraw(fd)
            else:
                if self._saved_termios_attrs is not None:
                    termios.tcsetattr(fd, termios.TCSANOW, self._saved_termios_attrs)
                    self._saved_termios_attrs = None
        except (ImportError, OSError, AttributeError):
            # termios/tty not available or not a TTY
            pass

    def read_char(self) -> Optional[str]:
        """Read a single character (requires raw mode).

        Returns:
            Character string or None if no input available
        """
        if not self.is_tty():
            return None

        try:
            import select

            fd = self._stdin.fileno() if hasattr(self._stdin, "fileno") else None
            if fd is None:
                return None

            # Check if input is available
            if select.select([fd], [], [], 0)[0]:
                return self._stdin.read(1)
            return None
        except (ImportError, OSError, AttributeError):
            return None

    def read_line(self) -> str:
        """Read a line of input.

        Returns:
            Line of text (without newline)
        """
        line = self._stdin.readline()
        return line.rstrip("\n\r")

    def read_password(self, prompt: str = "") -> str:
        """Read password with echo disabled.

        Args:
            prompt: Optional prompt to display

        Returns:
            Password string
        """
        if prompt:
            self.write(prompt)
            self.flush()

        self.set_echo(False)
        try:
            password = self.read_line()
            return password
        finally:
            self.set_echo(True)
            self.write("\n")
            self.flush()

    # State Queries (not applicable for RealConsole, but required by protocol)
    def get_cursor(self) -> Tuple[int, int]:
        """Get current cursor position (not available for RealConsole).

        Returns:
            Tuple of (0, 0) as placeholder
        """
        return (0, 0)

    def get_screen(self) -> List[List[str]]:
        """Get screen buffer (not available for RealConsole).

        Returns:
            Empty list as placeholder
        """
        return []

    def get_color(self) -> Tuple[Optional[int], Optional[int]]:
        """Get current color state (not available for RealConsole).

        Returns:
            Tuple of (None, None) as placeholder
        """
        return (None, None)

    def get_echo_enabled(self) -> bool:
        """Get echo state (not available for RealConsole).

        Returns:
            True as placeholder
        """
        return True

    def get_raw_mode(self) -> bool:
        """Get raw mode state (not available for RealConsole).

        Returns:
            False as placeholder
        """
        return False

    def get_events(self) -> List[TerminalEvent]:
        """Get event history (not available for RealConsole).

        Returns:
            Empty list as placeholder
        """
        return []


class MemoryConsole(BaseConsole):
    """In-memory console for testing.

    This console stores output in memory, allowing tests to capture
    and verify console output without actually printing to stdout.

    Example:
        >>> from pyiv.console import MemoryConsole
        >>>
        >>> console = MemoryConsole()
        >>> print("Test message", file=console)
        >>> print("Another line", file=console)
        >>>
        >>> # Get all captured output
        >>> output = console.getvalue()
        >>> assert "Test message" in output
        >>> assert "Another line" in output
        >>>
        >>> # Clear and reuse
        >>> console.seek(0)
        >>> console.truncate(0)
        >>> print("New output", file=console)
        >>> assert console.getvalue() == "New output\n"
    """

    def __init__(self):
        """Initialize in-memory console."""
        self._buffer = StringIO()

    def write(self, s: str) -> int:
        """Write string to memory buffer.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        return self._buffer.write(s)

    def flush(self) -> None:
        """Flush buffer (no-op for memory console)."""
        pass

    def writable(self) -> bool:
        """Check if console is writable.

        Returns:
            True (memory console is always writable)
        """
        return True

    def getvalue(self) -> str:
        """Get all captured output.

        Returns:
            All output written to the console as a string
        """
        return self._buffer.getvalue()

    def seek(self, pos: int) -> int:
        """Seek to position in buffer.

        Args:
            pos: Position to seek to

        Returns:
            New position
        """
        return self._buffer.seek(pos)

    def truncate(self, size: Optional[int] = None) -> int:
        """Truncate buffer to size.

        Args:
            size: Size to truncate to (None = current position)

        Returns:
            New size
        """
        return self._buffer.truncate(size)

    def close(self) -> None:
        """Close the buffer.

        Note: After closing, getvalue() will raise ValueError.
        To get the value before closing, call getvalue() first.
        """
        if not self._buffer.closed:
            self._buffer.close()


class FileConsole(BaseConsole):
    """File-based console for testing.

    This console writes output to a file, useful for testing scenarios
    where you want to verify output was written to a specific file.

    Example:
        >>> from pyiv.console import FileConsole
        >>> from pathlib import Path
        >>>
        >>> output_file = Path("/tmp/test_output.txt")
        >>> console = FileConsole(output_file)
        >>> print("Test message", file=console)
        >>> console.flush()
        >>>
        >>> # Verify output was written
        >>> content = output_file.read_text()
        >>> assert "Test message" in content
    """

    def __init__(self, file: Union[str, Path], mode: str = "w", encoding: str = "utf-8"):
        """Initialize file-based console.

        Args:
            file: File path to write to
            mode: File mode (default: "w" for write)
            encoding: Text encoding (default: "utf-8")
        """
        self._file_path = Path(file)
        self._mode = mode
        self._encoding = encoding
        self._stream: Optional[TextIO] = None
        self._open()

    def _open(self) -> None:
        """Open the file stream."""
        if self._stream is None or self._stream.closed:
            self._stream = open(  # type: ignore[assignment]
                self._file_path, self._mode, encoding=self._encoding
            )

    def write(self, s: str) -> int:
        """Write string to file.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        self._open()
        if self._stream is None:
            raise IOError("File stream is not open")
        return self._stream.write(s)

    def flush(self) -> None:
        """Flush file buffer."""
        if self._stream is not None:
            self._stream.flush()

    def writable(self) -> bool:
        """Check if file is writable.

        Returns:
            True if file mode supports writing
        """
        return "w" in self._mode or "a" in self._mode

    def close(self) -> None:
        """Close the file stream."""
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def __enter__(self) -> "FileConsole":
        """Context manager entry."""
        self._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


class PTYConsole(BaseConsole):
    """Pseudoterminal console for testing.

    This console creates a pseudoterminal (pty) that behaves like a real
    terminal. Use this for testing programs that require TTY behavior.

    Example:
        >>> from pyiv.console import PTYConsole
        >>>
        >>> with PTYConsole() as console:
        ...     assert console.is_tty() == True  # Always True
        ...     console.clear()
        ...     console.write("Test")
    """

    def __init__(self):
        """Initialize pseudoterminal console."""
        try:
            import pty

            self.master_fd, self.slave_fd = pty.openpty()
            self._stream = os.fdopen(self.master_fd, "w")
            self._stdin = os.fdopen(self.slave_fd, "r")
        except ImportError:
            raise RuntimeError("pty module not available on this platform")

    def write(self, s: str) -> int:
        """Write string to pty.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        return self._stream.write(s)

    def flush(self) -> None:
        """Flush pty buffer."""
        self._stream.flush()

    def writable(self) -> bool:
        """Check if pty is writable.

        Returns:
            True (pty is always writable)
        """
        return True

    def is_tty(self) -> bool:
        """Check if pty is a terminal (always True).

        Returns:
            True (pty always behaves as TTY)
        """
        return True

    def get_size(self) -> Tuple[int, int]:
        """Get pty size.

        Returns:
            Tuple of (columns, rows)
        """
        try:
            import pty

            size = pty._get_terminal_size(self.slave_fd)  # type: ignore[attr-defined]
            if size:
                return (size.columns, size.lines)
            return (80, 24)
        except (AttributeError, OSError):
            return (80, 24)

    def get_cursor_position(self) -> Optional[Tuple[int, int]]:
        """Get cursor position (not easily available from pty).

        Returns:
            None (not implemented for pty)
        """
        return None

    # Output Control - delegate to RealConsole logic
    def clear(self) -> None:
        """Clear the entire screen."""
        self.write(CLEAR_SCREEN)
        self.flush()

    def clear_line(self) -> None:
        """Clear the current line."""
        self.write(CLEAR_LINE)
        self.flush()

    def clear_to_end_of_line(self) -> None:
        """Clear from cursor to end of line."""
        self.write(CLEAR_TO_END_OF_LINE)
        self.flush()

    def move_cursor(self, x: int, y: int) -> None:
        """Move cursor to position."""
        self.write(f"\033[{y + 1};{x + 1}H")
        self.flush()

    def move_cursor_home(self) -> None:
        """Move cursor to home position."""
        self.write(CURSOR_HOME)
        self.flush()

    def move_cursor_up(self, n: int = 1) -> None:
        """Move cursor up n lines."""
        self.write(f"\033[{n}A")
        self.flush()

    def move_cursor_down(self, n: int = 1) -> None:
        """Move cursor down n lines."""
        self.write(f"\033[{n}B")
        self.flush()

    def move_cursor_left(self, n: int = 1) -> None:
        """Move cursor left n columns."""
        self.write(f"\033[{n}D")
        self.flush()

    def move_cursor_right(self, n: int = 1) -> None:
        """Move cursor right n columns."""
        self.write(f"\033[{n}C")
        self.flush()

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        self.write(HIDE_CURSOR)
        self.flush()

    def show_cursor(self) -> None:
        """Show the cursor."""
        self.write(SHOW_CURSOR)
        self.flush()

    def save_cursor(self) -> None:
        """Save current cursor position."""
        self.write("\033[s")
        self.flush()

    def restore_cursor(self) -> None:
        """Restore saved cursor position."""
        self.write("\033[u")
        self.flush()

    def set_color(self, fg: Optional[int] = None, bg: Optional[int] = None) -> None:
        """Set foreground and/or background color."""
        codes = []
        if fg is not None:
            codes.append(str(fg))
        if bg is not None:
            codes.append(str(bg))
        if codes:
            self.write(f"\033[{';'.join(codes)}m")
            self.flush()

    def reset_color(self) -> None:
        """Reset colors to default."""
        self.write(RESET_COLOR)
        self.flush()

    def bold(self, enabled: bool = True) -> None:
        """Enable or disable bold text."""
        if enabled:
            self.write(f"\033[{BOLD}m")
        else:
            self.write("\033[22m")
        self.flush()

    def underline(self, enabled: bool = True) -> None:
        """Enable or disable underline."""
        if enabled:
            self.write(f"\033[{UNDERLINE}m")
        else:
            self.write("\033[24m")
        self.flush()

    def set_echo(self, enabled: bool) -> None:
        """Turn echo on/off (not implemented for pty)."""
        # PTY echo control would require termios on slave_fd
        pass

    def set_raw_mode(self, enabled: bool) -> None:
        """Enable/disable raw mode (not implemented for pty)."""
        # PTY raw mode would require termios on slave_fd
        pass

    def read_char(self) -> Optional[str]:
        """Read a single character."""
        try:
            import select

            # Read from master_fd (what was written to pty)
            if select.select([self.master_fd], [], [], 0)[0]:
                return os.read(self.master_fd, 1).decode("utf-8", errors="ignore")
            return None
        except (ImportError, OSError):
            return None

    def read_line(self) -> str:
        """Read a line of input."""
        # For PTY, read from stdin (slave end)
        line = self._stdin.readline()
        return line.rstrip("\n\r")

    def read_password(self, prompt: str = "") -> str:
        """Read password (basic implementation)."""
        if prompt:
            self.write(prompt)
            self.flush()
        return self.read_line()

    def get_cursor(self) -> Tuple[int, int]:
        """Get cursor position (not available)."""
        return (0, 0)

    def get_screen(self) -> List[List[str]]:
        """Get screen buffer (not available)."""
        return []

    def get_color(self) -> Tuple[Optional[int], Optional[int]]:
        """Get color state (not available)."""
        return (None, None)

    def get_echo_enabled(self) -> bool:
        """Get echo state (not available)."""
        return True

    def get_raw_mode(self) -> bool:
        """Get raw mode state (not available)."""
        return False

    def get_events(self) -> List[TerminalEvent]:
        """Get event history (not available)."""
        return []

    def close(self) -> None:
        """Close the pty."""
        if hasattr(self, "_stream") and self._stream:
            self._stream.close()
        if hasattr(self, "_stdin") and self._stdin:
            self._stdin.close()
        if hasattr(self, "slave_fd"):
            try:
                os.close(self.slave_fd)
            except OSError:
                pass

    def __enter__(self) -> "PTYConsole":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


class MockConsole(BaseConsole):
    """Terminal state machine for testing.

    This console maintains a complete terminal state including screen buffer,
    cursor position, colors, and input state. Use this for testing terminal
    functionality with full state inspection and event tracking.

    Example:
        >>> from pyiv.console import MockConsole
        >>>
        >>> console = MockConsole(width=80, height=24)
        >>> console.clear()
        >>> console.move_cursor(10, 5)
        >>> console.set_color(fg=31)  # Red
        >>> console.write("Hello")
        >>>
        >>> # Inspect state
        >>> assert console.get_cursor() == (15, 5)
        >>> screen = console.get_screen()
        >>> assert screen[4][10:15] == "Hello"
        >>>
        >>> # Inspect events
        >>> events = console.get_events()
        >>> assert len(events) == 4
    """

    def __init__(self, width: int = 80, height: int = 24):
        """Initialize terminal state machine.

        Args:
            width: Terminal width in columns
            height: Terminal height in rows
        """
        self.width = width
        self.height = height
        self.cursor_x = 0
        self.cursor_y = 0
        self.screen = [[" "] * width for _ in range(height)]
        self.fg_color: Optional[int] = None
        self.bg_color: Optional[int] = None
        self._bold = False
        self._underline = False
        self.cursor_visible = True
        self.echo_enabled = True
        self.raw_mode = False
        self.input_buffer = ""
        self.events: List[TerminalEvent] = []
        self._saved_cursor_x = 0
        self._saved_cursor_y = 0

    def _add_event(self, event: TerminalEvent) -> None:
        """Add event to history."""
        self.events.append(event)

    def _parse_escape_sequence(self, s: str, pos: int) -> Tuple[int, Optional[str]]:
        """Parse ANSI escape sequence.

        Args:
            s: String containing escape sequence
            pos: Position of ESC character

        Returns:
            Tuple of (new_position, command_string or None)
        """
        if pos >= len(s) or s[pos] != ESC:
            return (pos, None)

        # Check for CSI (Control Sequence Introducer): ESC[
        if pos + 1 < len(s) and s[pos + 1] == "[":
            # Find the command character
            end = pos + 2
            while end < len(s) and not s[end].isalpha():
                end += 1
            if end < len(s) and s[end].isalpha():
                return (end + 1, s[pos : end + 1])

        # Check for other escape sequences
        if pos + 1 < len(s):
            char = s[pos + 1]
            if char in "su":  # Save/restore cursor
                return (pos + 2, s[pos : pos + 2])
            if char == "?" and pos + 4 < len(s):
                # Cursor visibility: ESC[?25h or ESC[?25l
                if s[pos + 2 : pos + 5] == "25":
                    return (pos + 5, s[pos : pos + 5])

        return (pos + 1, None)

    def _process_escape_sequence(self, seq: str) -> None:
        """Process an escape sequence and update state.

        Args:
            seq: Escape sequence string
        """
        if seq == CLEAR_SCREEN:
            self.clear()
        elif seq == CLEAR_LINE:
            # Clear current line
            self.screen[self.cursor_y] = [" "] * self.width
            self._add_event(ScreenClearEvent(time.time(), "line_clear"))
        elif seq == CURSOR_HOME:
            self.cursor_x = 0
            self.cursor_y = 0
            self._add_event(CursorMoveEvent(time.time(), "cursor_move", 0, 0))
        elif seq.startswith("\033[") and seq.endswith("H"):
            # Cursor position: ESC[row;colH
            try:
                parts = seq[2:-1].split(";")
                if len(parts) == 2:
                    row = int(parts[0]) - 1  # Convert to 0-based
                    col = int(parts[1]) - 1
                    self.cursor_x = max(0, min(col, self.width - 1))
                    self.cursor_y = max(0, min(row, self.height - 1))
                    self._add_event(
                        CursorMoveEvent(time.time(), "cursor_move", self.cursor_x, self.cursor_y)
                    )
            except (ValueError, IndexError):
                pass
        elif seq.startswith("\033[") and seq.endswith("m"):
            # Color/style: ESC[codem
            try:
                codes = seq[2:-1].split(";")
                old_fg = self.fg_color
                old_bg = self.bg_color
                for code_str in codes:
                    if not code_str:
                        continue
                    code = int(code_str)
                    if code == 0:
                        # Reset
                        self.fg_color = None
                        self.bg_color = None
                        self._bold = False
                        self._underline = False
                    elif code == 1:
                        self._bold = True
                    elif code == 4:
                        self._underline = True
                    elif code == 22:
                        self._bold = False
                    elif code == 24:
                        self._underline = False
                    elif 30 <= code <= 37:
                        self.fg_color = code
                    elif 40 <= code <= 47:
                        self.bg_color = code
                if self.fg_color != old_fg or self.bg_color != old_bg:
                    self._add_event(
                        ColorChangeEvent(time.time(), "color_change", self.fg_color, self.bg_color)
                    )
            except (ValueError, IndexError):
                pass
        elif seq == "\033[s":
            # Save cursor
            self._saved_cursor_x = self.cursor_x
            self._saved_cursor_y = self.cursor_y
        elif seq == "\033[u":
            # Restore cursor
            self.cursor_x = self._saved_cursor_x
            self.cursor_y = self._saved_cursor_y
            self._add_event(
                CursorMoveEvent(time.time(), "cursor_move", self.cursor_x, self.cursor_y)
            )
        elif seq == HIDE_CURSOR:
            self.cursor_visible = False
        elif seq == SHOW_CURSOR:
            self.cursor_visible = True

    def write(self, s: str) -> int:
        """Write string, parsing escape sequences and updating state.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        pos = 0
        written = 0

        while pos < len(s):
            # Look for escape sequence
            if s[pos] == ESC:
                new_pos, seq = self._parse_escape_sequence(s, pos)
                if seq:
                    self._process_escape_sequence(seq)
                    pos = new_pos
                    written += len(seq)
                    continue

            # Write character to screen
            char = s[pos]
            if char == "\n":
                self.cursor_y = min(self.cursor_y + 1, self.height - 1)
                self.cursor_x = 0
            elif char == "\r":
                self.cursor_x = 0
            elif char == "\t":
                # Tab: move to next tab stop (every 8 columns)
                self.cursor_x = (self.cursor_x // 8 + 1) * 8
                if self.cursor_x >= self.width:
                    self.cursor_x = 0
                    self.cursor_y = min(self.cursor_y + 1, self.height - 1)
            elif char == "\b":
                # Backspace
                if self.cursor_x > 0:
                    self.cursor_x -= 1
            else:
                # Regular character
                if 0 <= self.cursor_y < self.height and 0 <= self.cursor_x < self.width:
                    self.screen[self.cursor_y][self.cursor_x] = char
                    self.cursor_x += 1
                    if self.cursor_x >= self.width:
                        self.cursor_x = 0
                        self.cursor_y = min(self.cursor_y + 1, self.height - 1)

            pos += 1
            written += 1

        self._add_event(WriteEvent(time.time(), "write", s))
        return written

    def flush(self) -> None:
        """Flush buffer (no-op for mock console)."""
        pass

    def writable(self) -> bool:
        """Check if console is writable.

        Returns:
            True (mock console is always writable)
        """
        return True

    def is_tty(self) -> bool:
        """Check if console is a TTY (always False for mock).

        Returns:
            False (mock console is not a real TTY)
        """
        return False

    def get_size(self) -> Tuple[int, int]:
        """Get terminal size.

        Returns:
            Tuple of (columns, rows)
        """
        return (self.width, self.height)

    def get_cursor_position(self) -> Optional[Tuple[int, int]]:
        """Get current cursor position.

        Returns:
            Tuple of (x, y)
        """
        return (self.cursor_x, self.cursor_y)

    def clear(self) -> None:
        """Clear the entire screen."""
        self.screen = [[" "] * self.width for _ in range(self.height)]
        self.cursor_x = 0
        self.cursor_y = 0
        self._add_event(ScreenClearEvent(time.time(), "screen_clear"))

    def clear_line(self) -> None:
        """Clear the current line."""
        if 0 <= self.cursor_y < self.height:
            self.screen[self.cursor_y] = [" "] * self.width
        self._add_event(ScreenClearEvent(time.time(), "line_clear"))

    def clear_to_end_of_line(self) -> None:
        """Clear from cursor to end of line."""
        if 0 <= self.cursor_y < self.height:
            for x in range(self.cursor_x, self.width):
                self.screen[self.cursor_y][x] = " "

    def move_cursor(self, x: int, y: int) -> None:
        """Move cursor to position."""
        old_x, old_y = self.cursor_x, self.cursor_y
        self.cursor_x = max(0, min(x, self.width - 1))
        self.cursor_y = max(0, min(y, self.height - 1))
        if self.cursor_x != old_x or self.cursor_y != old_y:
            self._add_event(
                CursorMoveEvent(time.time(), "cursor_move", self.cursor_x, self.cursor_y)
            )

    def move_cursor_home(self) -> None:
        """Move cursor to home position."""
        self.move_cursor(0, 0)

    def move_cursor_up(self, n: int = 1) -> None:
        """Move cursor up n lines."""
        self.move_cursor(self.cursor_x, self.cursor_y - n)

    def move_cursor_down(self, n: int = 1) -> None:
        """Move cursor down n lines."""
        self.move_cursor(self.cursor_x, self.cursor_y + n)

    def move_cursor_left(self, n: int = 1) -> None:
        """Move cursor left n columns."""
        self.move_cursor(self.cursor_x - n, self.cursor_y)

    def move_cursor_right(self, n: int = 1) -> None:
        """Move cursor right n columns."""
        self.move_cursor(self.cursor_x + n, self.cursor_y)

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        self.cursor_visible = False

    def show_cursor(self) -> None:
        """Show the cursor."""
        self.cursor_visible = True

    def save_cursor(self) -> None:
        """Save current cursor position."""
        self._saved_cursor_x = self.cursor_x
        self._saved_cursor_y = self.cursor_y

    def restore_cursor(self) -> None:
        """Restore saved cursor position."""
        self.move_cursor(self._saved_cursor_x, self._saved_cursor_y)

    def set_color(self, fg: Optional[int] = None, bg: Optional[int] = None) -> None:
        """Set foreground and/or background color."""
        old_fg, old_bg = self.fg_color, self.bg_color
        if fg is not None:
            self.fg_color = fg
        if bg is not None:
            self.bg_color = bg
        if self.fg_color != old_fg or self.bg_color != old_bg:
            self._add_event(
                ColorChangeEvent(time.time(), "color_change", self.fg_color, self.bg_color)
            )

    def reset_color(self) -> None:
        """Reset colors to default."""
        old_fg, old_bg = self.fg_color, self.bg_color
        self.fg_color = None
        self.bg_color = None
        self._bold = False
        self._underline = False
        if old_fg is not None or old_bg is not None:
            self._add_event(ColorChangeEvent(time.time(), "color_change", None, None))

    def bold(self, enabled: bool = True) -> None:
        """Enable or disable bold text."""
        self._bold = enabled

    def underline(self, enabled: bool = True) -> None:
        """Enable or disable underline."""
        self._underline = enabled

    def set_echo(self, enabled: bool) -> None:
        """Turn echo on/off for password prompts."""
        old_state = self.echo_enabled
        self.echo_enabled = enabled
        self._add_event(EchoChangeEvent(time.time(), "echo_change", enabled, old_state))

    def set_raw_mode(self, enabled: bool) -> None:
        """Enable/disable raw mode."""
        old_state = self.raw_mode
        self.raw_mode = enabled
        self._add_event(RawModeChangeEvent(time.time(), "raw_mode_change", enabled, old_state))

    def read_char(self) -> Optional[str]:
        """Read a single character from input buffer."""
        if self.input_buffer:
            char = self.input_buffer[0]
            self.input_buffer = self.input_buffer[1:]
            self._add_event(InputEvent(time.time(), "input", char))
            return char
        return None

    def read_line(self) -> str:
        """Read a line from input buffer."""
        if "\n" in self.input_buffer:
            idx = self.input_buffer.index("\n")
            line = self.input_buffer[:idx]
            self.input_buffer = self.input_buffer[idx + 1 :]
        else:
            line = self.input_buffer
            self.input_buffer = ""
        self._add_event(InputEvent(time.time(), "input", line))
        return line

    def read_password(self, prompt: str = "") -> str:
        """Read password with echo disabled."""
        if prompt:
            self.write(prompt)
            self.flush()

        self.set_echo(False)
        try:
            password = self.read_line()
            return password
        finally:
            self.set_echo(True)
            self.write("\n")
            self.flush()

    def simulate_input(self, text: str) -> None:
        """Simulate input for testing.

        Args:
            text: Text to add to input buffer
        """
        self.input_buffer += text

    def get_cursor(self) -> Tuple[int, int]:
        """Get current cursor position.

        Returns:
            Tuple of (x, y)
        """
        return (self.cursor_x, self.cursor_y)

    def get_screen(self) -> List[List[str]]:
        """Get screen buffer (copy).

        Returns:
            2D list of screen contents
        """
        return [row[:] for row in self.screen]

    def get_screen_line(self, y: int) -> str:
        """Get specific line from screen.

        Args:
            y: Line number (0-based)

        Returns:
            Line contents as string
        """
        if 0 <= y < self.height:
            return "".join(self.screen[y])
        return ""

    def get_screen_char(self, x: int, y: int) -> str:
        """Get character at position.

        Args:
            x: Column (0-based)
            y: Row (0-based)

        Returns:
            Character at position
        """
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.screen[y][x]
        return " "

    def get_color(self) -> Tuple[Optional[int], Optional[int]]:
        """Get current color state.

        Returns:
            Tuple of (fg, bg)
        """
        return (self.fg_color, self.bg_color)

    def get_style(self) -> Dict[str, bool]:
        """Get text style state.

        Returns:
            Dictionary of style flags
        """
        return {"bold": self._bold, "underline": self._underline}

    def get_echo_enabled(self) -> bool:
        """Get echo state.

        Returns:
            True if echo is enabled
        """
        return self.echo_enabled

    def get_raw_mode(self) -> bool:
        """Get raw mode state.

        Returns:
            True if raw mode is enabled
        """
        return self.raw_mode

    def get_events(self) -> List[TerminalEvent]:
        """Get event history.

        Returns:
            List of terminal events
        """
        return self.events[:]

    def clear_state(self) -> None:
        """Clear all state (for test setup)."""
        self.clear()
        self.fg_color = None
        self.bg_color = None
        self._bold = False
        self._underline = False
        self.cursor_visible = True
        self.echo_enabled = True
        self.raw_mode = False
        self.input_buffer = ""
        self.events = []
        self._saved_cursor_x = 0
        self._saved_cursor_y = 0
