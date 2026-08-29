Keys and collections
====================

Several implementations of one type need a qualifier. Several implementations
**as a set or list** use a multibinder.

Qualified keys
--------------

``Key(Type, Named("..."))`` is the Guice-style named binding:

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

Optional dependencies
---------------------

``Optional[T]`` injects the binding or ``None``. Use an **ABC** (or another
type the injector cannot construct) for ``T``. A concrete class with no
binding is still built:

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
