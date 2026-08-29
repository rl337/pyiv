Testing with doubles
====================

Bind production types in one config and in-memory doubles in another. Tests
should not mock ``time``, the filesystem, or ``sys.stdout``.

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.clock import Clock, RealClock, SyntheticClock
   from pyiv.console import Console, MemoryConsole, RealConsole
   from pyiv.datetime_service import DateTimeService, MockDateTimeService, PythonDateTimeService
   from pyiv.filesystem import Filesystem, MemoryFilesystem, RealFilesystem

   class ProdConfig(Config):
       def configure(self):
           self.register(Clock, RealClock)
           self.register(Filesystem, RealFilesystem)
           self.register(Console, RealConsole)
           self.register(DateTimeService, PythonDateTimeService)

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

   injector = get_injector(TestConfig)
   clock = injector.inject(Clock)
   clock.advance(5.0)
   clock.time()  # 105.0

   fs = injector.inject(Filesystem)
   fs.write_text("test.txt", "content")  # in memory, not the repo

   console = injector.inject(Console)
   print("hello", file=console)
   console.getvalue()  # contains "hello"

What to swap
------------

* **Clock / SyntheticClock** — freeze and advance time; no real sleeps.
* **Filesystem / MemoryFilesystem** — read and write paths without touching disk.
* **Console / MemoryConsole** — capture ``print(..., file=console)``.
* **DateTimeService / MockDateTimeService** — fixed UTC timestamps.

Keep the rest of the object graph on real classes. Only replace the edges that
talk to the world.

See also :doc:`/pyiv/pyiv.clock`, :doc:`/pyiv/pyiv.filesystem`,
:doc:`/pyiv/pyiv.console`, and :doc:`/pyiv/pyiv.datetime_service`.
