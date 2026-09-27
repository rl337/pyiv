Keys and collections
====================

Several implementations of one type need a qualifier. Several implementations
**as a set or list** use a multibinder.

Qualified keys
--------------

``Key(Type, Named("..."))`` is the Guice-style named binding. ``Named`` accepts
a string **or** a list/tuple of tags (stored as a set). Scalar and singleton
list are the same key: ``Named("json") == Named(["json"])``.

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.key import Key, Named

   class Database:
       def __init__(self, name: str):
           self.name = name

   class PostgreSQL(Database):
       def __init__(self):
           super().__init__("postgresql")

   class MySQL(Database):
       def __init__(self):
           super().__init__("mysql")

   class MyConfig(Config):
       def configure(self):
           self.register_key(Key(Database, Named("primary")), PostgreSQL)
           self.register_key(Key(Database, Named("replica")), MySQL)

   injector = get_injector(MyConfig)
   injector.inject(Key(Database, Named("primary")))  # PostgreSQL
   injector.inject(Key(Database, Named("replica")))  # MySQL

Binder equivalent: ``binder.bind_key(Key(Database, Named("primary"))).to(...)``.

Compound tags and defaults
--------------------------

Register multiple tag sets for the same type. Mark at most one with
``default=True`` for bare ``inject(Type)`` and ``Matched`` tie-breaks.
Identical tag sets for the same type raise at registration (unless an
``install`` merge replaces them).

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.key import Key, Named, Matched

   class Encoder:
       def __init__(self, kind: str):
           self.kind = kind

   class JSONEncoder(Encoder):
       def __init__(self):
           super().__init__("json")

   class PrettyJSONEncoder(Encoder):
       def __init__(self):
           super().__init__("pretty")

   class EncoderConfig(Config):
       def configure(self):
           self.register_key(Key(Encoder, Named("json")), JSONEncoder)
           self.register_key(
               Key(Encoder, Named(["json", "pretty"], default=True)),
               PrettyJSONEncoder,
           )

   inj = get_injector(EncoderConfig)
   inj.inject(Key(Encoder, Named("json")))  # JSONEncoder (strict)
   inj.inject(Key(Encoder, Matched(required=["json"], prefer=["pretty"])))
   inj.inject(Encoder)  # PrettyJSONEncoder via default=True

Strict vs matched injection
---------------------------

- **``Named`` on inject** — exact tag-set equality.
- **``Matched(required=..., prefer=...)``** — inject-only. Candidates are Named
  bindings for the type where ``required ⊆ tags``. Among those, maximize
  ``|prefer ∩ tags|``; remaining ties use ``default=True``; still ambiguous
  raises ``CreationError``.
- **Bare ``inject(Type)``** — unqualified binding first (if any); else the
  unique ``default=True`` Named binding, or the sole Named binding; otherwise
  ambiguous / missing.

Do not pass ``Matched`` to ``register_key`` / ``bind_key``.

When to use multibinder instead
-------------------------------

Use **Named / Matched** when the caller wants **one** implementation selected
by tags. Use a **multibinder** when the caller wants **all** implementations
as a ``Set``, ``List``, or ``Dict``.

Multibinder
-----------

Register many implementations and inject ``Set[T]`` or ``List[T]``. Inject
the collection through a **host class constructor**, not
``injector.inject(Set[T])``:

.. code-block:: python

   from typing import Set

   from pyiv import Config, get_injector

   class EventHandler:
       pass

   class EmailHandler(EventHandler):
       pass

   class SMSHandler(EventHandler):
       pass

   class HandlerHost:
       def __init__(self, handlers: Set[EventHandler]):
           self.handlers = handlers

   class MyConfig(Config):
       def configure(self):
           mb = self.multibinder(EventHandler, as_set=True)
           mb.add(EmailHandler)
           mb.add(SMSHandler)

   host = get_injector(MyConfig).inject(HandlerHost)
   # host.handlers is EmailHandler and SMSHandler

``as_set=False`` binds ``List[T]`` and preserves add order.

Map multibinder
---------------

Keyed implementations inject as ``Dict[K, V]`` through a host constructor:

.. code-block:: python

   from typing import Dict

   from pyiv import Config, get_injector

   class Encoder:
       pass

   class JsonEncoder(Encoder):
       pass

   class XmlEncoder(Encoder):
       pass

   class EncoderHost:
       def __init__(self, encoders: Dict[str, Encoder]):
           self.encoders = encoders

   class MyConfig(Config):
       def configure(self):
           mb = self.map_multibinder(Encoder)
           mb.add("json", JsonEncoder)
           mb.add("xml", XmlEncoder)

   host = get_injector(MyConfig).inject(EncoderHost)
   # host.encoders["json"] is JsonEncoder

Optional dependencies
---------------------

``Optional[T]`` injects the binding or ``None``. Use an **ABC** (or another
type the injector cannot construct) for ``T``. A concrete class with no
binding is still built. Ambiguous Named resolution (multiple tags, no unique
default) raises ``CreationError`` — ambiguity is not treated as missing.

.. code-block:: python

   from abc import ABC
   from typing import Optional

   from pyiv import Config, get_injector

   class Cache(ABC):
       pass

   class Service:
       def __init__(self, cache: Optional[Cache] = None):
           self.cache = cache

   class NoCacheConfig(Config):
       def configure(self):
           pass  # Cache not registered

   get_injector(NoCacheConfig).inject(Service).cache is None  # True

See also :doc:`/pyiv/pyiv.key`, :doc:`/pyiv/pyiv.multibinder`, and
:doc:`/pyiv/pyiv.optional`.
