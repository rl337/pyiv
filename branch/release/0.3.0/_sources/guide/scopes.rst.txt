Scopes
======

A scope decides whether ``inject()`` returns a new object or a cached one.

Default (no scope)
------------------

Each ``inject()`` call constructs a new instance:

.. code-block:: python

   from pyiv import Config, get_injector

   class Logger:
       pass

   class FileLogger(Logger):
       pass

   class MyConfig(Config):
       def configure(self):
           self.register(Logger, FileLogger)

   injector = get_injector(MyConfig)
   injector.inject(Logger) is injector.inject(Logger)  # False

Per-injector singleton
----------------------

One instance **per** ``Injector``. Separate ``get_injector()`` calls do not
share it:

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.scope import SingletonScope

   class MyConfig(Config):
       def configure(self):
           self.register(Logger, FileLogger, singleton=True)
           # equivalent: scope=SingletonScope()

   a = get_injector(MyConfig)
   b = get_injector(MyConfig)
   a.inject(Logger) is a.inject(Logger)  # True
   a.inject(Logger) is b.inject(Logger)  # False

Process-wide singleton
----------------------

``GlobalSingletonScope`` (or ``SingletonType.GLOBAL_SINGLETON``) caches one
instance for the whole process. Use it for things like a process-wide cache;
avoid it in tests unless you reset that cache.

Custom scopes
-------------

Implement :class:`~pyiv.scope.Scope` when you need request, thread, or
session lifetime. Built-in scopes are enough for most apps.

See also :doc:`/pyiv/pyiv.scope` and :doc:`/pyiv/pyiv.singleton`.
