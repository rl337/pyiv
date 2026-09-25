Binding
=======

Register an abstract type once. The injector builds constructor arguments from
annotations.

``Config.register``
-------------------

The direct API. ``concrete`` can be a class or a zero-argument factory:

.. code-block:: python

   from pyiv import Config, get_injector

   class Database:
       pass

   class PostgreSQL(Database):
       pass

   class Logger:
       pass

   class FileLogger(Logger):
       pass

   class MyConfig(Config):
       def configure(self):
           self.register(Database, PostgreSQL)
           self.register(Logger, FileLogger, singleton=True)

   injector = get_injector(MyConfig)
   injector.inject(Database)  # PostgreSQL

``singleton=True`` is a per-injector singleton. See :doc:`scopes` for
``Scope`` and process-wide singletons.

Binder
------

``get_binder()`` is the same registrations with a fluent chain. Use it when
you want ``.to(...)``, ``.to_instance(...)``, or ``.in_scope(...)`` in one
expression:

.. code-block:: python

   from pyiv import Config
   from pyiv.scope import SingletonScope

   class Cache:
       pass

   class MyConfig(Config):
       def configure(self):
           binder = self.get_binder()
           binder.bind(Database).to(PostgreSQL)
           binder.bind(Logger).to(FileLogger).in_scope(SingletonScope())
           binder.bind_instance(Cache, Cache())

``register`` and Binder write the same config. Pick one style per project;
mixing them in one ``configure()`` is fine.

Installing modules
------------------

``install`` merges another ``Config`` into this one. Later installs overwrite
the same type or key (last wins). Use :func:`pyiv.override.override` when you
want an explicit base/override overlay for tests.

.. code-block:: python

   from pyiv import Config, get_injector

   class Database:
       pass

   class PostgreSQL(Database):
       pass

   class DbConfig(Config):
       def configure(self):
           self.register(Database, PostgreSQL)

   class AppConfig(Config):
       def configure(self):
           self.install(DbConfig)

   get_injector(AppConfig).inject(Database)  # PostgreSQL

Untargeted bindings
-------------------

``binder.bind(Concrete)`` without ``.to(...)`` registers a self-binding
(needed for explicit-binding mode and private modules):

.. code-block:: python

   class Service:
       pass

   class MyConfig(Config):
       def configure(self):
           self.get_binder().bind(Service)

Stages
------

``get_injector(config, stage=Stage.PRODUCTION)`` eagerly creates
singleton-scoped bindings at build time so misconfiguration fails fast.
The default is ``Stage.DEVELOPMENT`` (lazy).

See also :doc:`hierarchy` for child injectors and private modules.

Unregistered concrete types
---------------------------

If you ``inject()`` a **concrete** class that was never registered, the
injector still constructs it and fills its annotated parameters (unless
``require_explicit_bindings()`` is set). Interfaces and ABCs must be bound
(or marked optional — see :doc:`keys`). Concrete constructor dependencies
are also just-in-time constructed when explicit mode is off.

See also :doc:`/pyiv/pyiv.config` and :doc:`/pyiv/pyiv.binder`.
