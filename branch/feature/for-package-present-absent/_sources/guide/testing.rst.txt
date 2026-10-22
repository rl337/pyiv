Testing with doubles
====================

Bind production types in one config and in-memory doubles in another. Tests
should not mock ``time``, the filesystem, ``os.environ``, ``subprocess``,
``logging.getLogger``, or ``sys.stdout``.

Prefer use-case packages (``pyiv.files``, ``pyiv.time``, ``pyiv.log``,
``pyiv.process``). Legacy top-level modules still re-export for compatibility.

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.console import Console, MemoryConsole, RealConsole
   from pyiv.files import Filesystem, MemoryFilesystem, RealFilesystem
   from pyiv.log import LoggerFactory, MemoryLoggerFactory, StdlibLoggerFactory
   from pyiv.process import Environment, MemoryEnvironment, OsEnvironment
   from pyiv.time import Clock, DateTimeService, MockDateTimeService, PythonDateTimeService, RealClock, SyntheticClock

   class ProdConfig(Config):
       def configure(self):
           self.register(Clock, RealClock)
           self.register(Filesystem, RealFilesystem)
           self.register(Console, RealConsole)
           self.register(DateTimeService, PythonDateTimeService)
           self.register(Environment, OsEnvironment)
           self.register(LoggerFactory, StdlibLoggerFactory)

   class TestConfig(Config):
       def configure(self):
           self.register(
               Clock,
               lambda: SyntheticClock(start_time=100.0),
               singleton=True,
           )
           self.register(Filesystem, MemoryFilesystem)
           self.register(Console, MemoryConsole)
           self.register(DateTimeService, MockDateTimeService)
           self.register(Environment, MemoryEnvironment)
           self.register(LoggerFactory, MemoryLoggerFactory)

   injector = get_injector(TestConfig)
   clock = injector.inject(Clock)
   clock.advance(5.0)
   clock.time()  # 105.0

   fs = injector.inject(Filesystem)
   fs.write_text("/test.txt", "content")  # in memory, not the repo

   console = injector.inject(Console)
   print("hello", file=console)
   console.getvalue()  # contains "hello"

What to swap
------------

* **Clock / SyntheticClock** — freeze and advance time; no real sleeps.
* **Filesystem / MemoryFilesystem** — read and write paths without touching disk.
  Mount zip/tar or a fake ``/proc`` with ``MountFilesystem`` /
  ``MappingFilesystem``.
* **Console / MemoryConsole** — capture ``print(..., file=console)``.
* **DateTimeService / MockDateTimeService** — fixed UTC timestamps.
* **Environment / MemoryEnvironment** — no ``os.environ`` residue.
* **ProcessRunner / MemoryProcessRunner** — scripted argv results.
* **Logger / MemoryLogger** (via ``LoggerFactory``) — assert diagnostics;
  use ``LogSetup`` + ``add_logging_args`` for CLI verbosity.
* **Entropy / SyntheticEntropy**, **Hasher / SyntheticHasher** — deterministic
  tokens and digests.

Keep the rest of the object graph on real classes. Only replace the edges that
talk to the world.

Override overlays
-----------------

When the production graph is large, overlay only the doubles with
``override(ProdConfig).with_(TestConfig)`` instead of rewriting every binding:

.. code-block:: python

   from pyiv import get_injector, override
   from pyiv.time import Clock, SyntheticClock

   class TestOverrides(Config):
       def configure(self):
           self.register(
               Clock,
               lambda: SyntheticClock(start_time=100.0),
               singleton=True,
           )

   injector = get_injector(override(ProdConfig).with_(TestOverrides))

See also :doc:`/pyiv/pyiv.files`, :doc:`/pyiv/pyiv.time`, :doc:`/pyiv/pyiv.log`,
:doc:`/pyiv/pyiv.process`, :doc:`/pyiv/pyiv.console`, and
:doc:`/inspiration/stdlib-injectable-surfaces`.
