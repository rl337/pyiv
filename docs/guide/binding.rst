Binding
=======

Register an abstract type once. The injector builds constructor arguments from
annotations (including ``Annotated[T, Named(...)]`` /
``Annotated[T, Matched(...)]`` — see :doc:`keys`).

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

Contextual bindings (when-injected-into)
----------------------------------------

Bind a default implementation, then override it **only** when the type is
requested while constructing a specific owner class (exact type match; no
subclass walk). This is orthogonal to :doc:`keys` (``Named`` / ``Matched``).

.. code-block:: python

   from pyiv import Config, get_injector

   class Encoder:
       def __init__(self, kind: str = "base"):
           self.kind = kind

   class JSONEncoder(Encoder):
       def __init__(self):
           super().__init__("json")

   class AvroEncoder(Encoder):
       def __init__(self):
           super().__init__("avro")

   class AvroProducer:
       def __init__(self, encoder: Encoder):
           self.encoder = encoder

   class MyConfig(Config):
       def configure(self):
           binder = self.get_binder()
           binder.bind(Encoder).to(JSONEncoder)
           binder.bind(Encoder).to(AvroEncoder).when_injected_into(AvroProducer)
           binder.bind(AvroProducer).to(AvroProducer)

   inj = get_injector(MyConfig)
   inj.inject(Encoder)  # JSONEncoder (default)
   inj.inject(AvroProducer).encoder  # AvroEncoder (automatic via owner stack)
   inj.inject(Encoder, from_=AvroProducer)  # AvroEncoder (manual)

``Config.register(..., when_injected_into=Owner)`` and
``register_instance`` / ``register_provider`` accept the same flag.
``from_`` on ``inject()`` is reserved by the injector and is never forwarded
to constructors. Contextual bindings apply to **bare types** only; they do
not affect ``inject(Key(...))``.

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
(or marked optional — see :doc:`keys`). For multiple implementations of one
type, use :doc:`keys` (``Named`` tag sets / ``Matched``, including
``Annotated`` on constructor parameters) or contextual
``when_injected_into`` bindings above. Field injection via
``inject_members`` does **not** honor Annotated qualifiers — use a
constructor or ``inject(Key(...))``. Concrete constructor dependencies
are also just-in-time constructed when explicit mode is off.

See also :doc:`/pyiv/pyiv.config` and :doc:`/pyiv/pyiv.binder`.
