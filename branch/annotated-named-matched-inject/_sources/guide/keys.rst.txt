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

Annotated constructor injection
-------------------------------

Constructor parameters can carry ``Named`` or ``Matched`` via
``typing.Annotated`` so you do not call ``inject(Key(...))`` by hand:

.. code-block:: python

   from typing import Annotated, Optional

   from pyiv import Config, Provider, get_injector
   from pyiv.key import Key, Named, Matched

   class Completer:
       def __init__(self, kind: str = ""):
           self.kind = kind

   class DeepCompleter(Completer):
       def __init__(self):
           super().__init__("deep")

   class CodeReviewHarness:
       def __init__(
           self,
           inference: Annotated[Completer, Named(["reason", "code", "deep"])],
           judge: Annotated[Provider[Completer], Named(["judge", "heavy"])],
           summarize: Annotated[
               Optional[Completer],
               Matched(required=["reason", "summarize"]),
           ] = None,
       ):
           self.inference = inference
           self.judge = judge
           self.summarize = summarize

   class HarnessConfig(Config):
       def configure(self):
           self.register_key(
               Key(Completer, Named(["reason", "code", "deep"])),
               DeepCompleter,
           )
           self.register_key(
               Key(Completer, Named(["judge", "heavy"])),
               DeepCompleter,
           )

   host = get_injector(HarnessConfig).inject(CodeReviewHarness)
   # host.inference is DeepCompleter; summarize is None (no candidate);
   # host.judge.get() lazily resolves the Named binding

Rules:

- ``Annotated[T, Named(...)]`` — strict tag-set match
- ``Annotated[T, Matched(...)]`` — nearest-match ladder
- ``Annotated[Optional[T], Q]`` / ``Annotated[T | None, Q]`` — ``None`` only
  when there is **no** candidate; ambiguity still raises
- ``Annotated[Provider[T], Q]`` — lazy ``Provider`` that still qualifies on
  ``get()``
- At most one ``Named`` or ``Matched`` in the Annotated metadata; a second
  qualifier raises ``CreationError``. Other metadata is ignored.

You can still call ``injector.inject(Key(...))`` explicitly; Annotated is
sugar for constructor (and factory) parameters.

Where Annotated Named / Matched does **not** work
-------------------------------------------------

These are intentional limits (use ``inject(Key(...))`` or redesign instead):

- **Field / members injection** — ``inject_members`` / ``MembersInjector``
  resolve bare field types only. ``Annotated[T, Named(...)]`` on a dataclass
  or class attribute is **not** honored. Prefer constructor injection, or
  assign ``injector.inject(Key(...))`` yourself after construction.
- **Registration** — ``Matched`` is inject-only. Never pass ``Matched`` (or
  ``Annotated``) to ``register_key`` / ``bind_key``; register with ``Named``.
- **Bare ``inject(Annotated[...])``** — call ``inject(Key(T, Named|Matched))``
  or inject a host class whose constructor uses Annotated. Passing an
  ``Annotated`` alias as the inject target is not supported.
- **Multibinder collections** — ``Set[T]`` / ``List[T]`` / ``Dict[K, V]``
  constructor params are not combined with Named/Matched metadata. Qualify
  individual deps, or use map multibinder keys separately.
- **Custom ``Qualifier`` types** — only ``Named`` and ``Matched`` are read
  from Annotated metadata. Other qualifier objects still work only via
  exact ``Key(T, qualifier)`` lookup.
- **Python 3.8**: ``typing.Annotated`` is 3.9+. On 3.8 use
  ``typing_extensions.Annotated`` in application code (pyiv does not depend
  on ``typing_extensions``). Detection of either Annotated origin is supported.

When to use multibinder instead
-------------------------------

Use **Named / Matched** when the caller wants **one** implementation selected
by tags (via ``Key``, ``Annotated`` on a constructor param, or bare
``inject(Type)`` with ``default=True``). Use a **multibinder** when the
caller wants **all** implementations as a ``Set``, ``List``, or ``Dict``.
Do not put Named/Matched metadata on the collection annotation itself.

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
binding is still built. Ambiguous Named / Matched resolution (multiple
candidates, no unique default) raises ``CreationError`` — ambiguity is not
treated as missing. The same rule applies to
``Annotated[Optional[T], Named|Matched]`` on constructors.

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
