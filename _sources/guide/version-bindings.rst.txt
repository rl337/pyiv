Version-conditioned bindings
============================

Select among several implementations of the same interface based on a
**named version domain** — the running Python interpreter, an installed
distribution, or any host-defined domain (OS release, wire protocol, …).

See :mod:`pyiv.version` for the full API (sources, parsers, candidates) and
:mod:`pyiv.pep440` for the built-in :pep:`440` engine. This page is the how-to.

Fluent API
----------

``for_python_version``, ``for_package_version``, ``for_package_present``,
and ``for_package_absent`` are convenience adapters over ``for_version``.
The version helpers use the named parser ``\"PEP440\"``
(:class:`~pyiv.pep440.Pep440VersionParser`). Presence / absence helpers match
without a PEP 440 parse.

Interpreter version
~~~~~~~~~~~~~~~~~~~

Interpreter version is read through an injectable
:class:`~pyiv.version.PythonVersionProvider`. Production defaults to
:class:`~pyiv.version.SysPythonVersionProvider`. Tests bind
:class:`~pyiv.version.FixedPythonVersionProvider` so the same graph can be
checked under many Python versions:

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.version import FixedPythonVersionProvider, PythonVersionProvider

   class Runner:
       kind = "base"

   class LegacyRunner(Runner):
       kind = "legacy"

   class ModernRunner(Runner):
       kind = "modern"

   class RunnerConfig(Config):
       def configure(self):
           binder = self.get_binder()
           # Omit in production — for_python_version binds SysPythonVersionProvider.
           binder.bind(PythonVersionProvider).to_instance(
               FixedPythonVersionProvider("3.10.12")
           )
           binder.bind(Runner).to(LegacyRunner).for_python_version("<3.11")
           binder.bind(Runner).to(ModernRunner).for_python_version(">=3.11")

   inj = get_injector(RunnerConfig)
   assert inj.inject(Runner).kind == "legacy"
   assert inj.inject(PythonVersionProvider).get_version() == "3.10.12"

Optional package present / absent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Prefer an optional accelerator when its **distribution** is installed, and a
stdlib (or other) implementation when it is missing. Pair
``for_package_present`` with ``for_package_absent`` so exactly one candidate
matches (no unconditional fallback required). See
:ref:`package-presence-absence` for fallback ordering and testing tips.

.. code-block:: python

   from pyiv import Config, get_injector

   class Encoder:
       kind = "base"

   class CJsonEncoder(Encoder):
       kind = "cjson"

   class JsonEncoder(Encoder):
       kind = "json"

   class EncoderConfig(Config):
       def configure(self):
           binder = self.get_binder()
           binder.bind(Encoder).to(CJsonEncoder).for_package_present("cjson")
           binder.bind(Encoder).to(JsonEncoder).for_package_absent("cjson")

Custom domains and named parsers
--------------------------------

Register a :class:`~pyiv.version.VersionSource` for the domain. Register a
custom :class:`~pyiv.version.VersionParser` under a name when versions are
not PEP 440 (for example an OS release string), then point the domain at that
name. Parsers raise :class:`~pyiv.version.InvalidVersion` (or a subclass) on
bad input.

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.version import InvalidVersion, MapVersionSource

   class FsTool:
       name = "base"

   class AlpineFs(FsTool):
       name = "alpine"

   class AlpineVersionParser:
       def is_version_compatible(self, version, specifier):
           if not specifier.startswith(">="):
               raise InvalidVersion(f"unsupported specifier: {specifier!r}")
           return self._tuple(version) >= self._tuple(specifier[2:])

       def is_version_less(self, a, b):
           return self._tuple(a) < self._tuple(b)

       def is_version_greater(self, a, b):
           return self._tuple(a) > self._tuple(b)

       def _tuple(self, s):
           return tuple(int(p) for p in s.split("."))

   class OsConfig(Config):
       def configure(self):
           binder = self.get_binder()
           binder.version_parser("alpine-release", AlpineVersionParser())
           binder.version_source("alpine", MapVersionSource({"alpine": "3.19.0"}))
           binder.use_version_parser("alpine", "alpine-release")
           binder.bind(FsTool).to(AlpineFs).for_version("alpine", ">=3.18")

   assert get_injector(OsConfig).inject(FsTool).name == "alpine"

Selection rules
---------------

- Candidates accumulate across ``install`` / ``override`` (they do not
  last-wins overwrite each other).
- Selection runs once at injector construction (environment-stable).
- Exactly one matching candidate wins; overlapping matches raise
  :class:`~pyiv.errors.CreationError` (ambiguous).
- Zero matches: an unconditional binding for the same type is used as a
  **fallback**. Register the fallback **after** the version-conditioned
  binds so ``.to(...)`` does not overwrite it before ``for_version``
  retracts the conditional registration.
- Missing distribution / absent version is a distinct diagnostic (not a
  silent wrong pick).

Mixing with other bindings
--------------------------

Version candidates live in a **separate store** from ordinary
``register`` / ``bind(...).to(...)`` registrations. At injector
construction pyiv selects among candidates, then materializes the winner
into the ordinary stores (or leaves an existing unconditional binding
alone as fallback). The rules below are locked by
``tests/test_version_binding_mixtures.py``.

**Match vs fallback**

1. If exactly one candidate matches the environment, that binding is used
   even when an unconditional binding for the same type also exists.
2. If zero candidates match and an unconditional binding exists, that
   unconditional binding is the fallback.
3. If zero candidates match and there is no unconditional binding,
   construction raises :class:`~pyiv.errors.CreationError`.
4. If two or more candidates match, construction raises an ambiguous
   :class:`~pyiv.errors.CreationError` — an unconditional fallback does
   **not** break the tie.

**Ordering (important)**

Register version-conditioned binds first, then the unconditional fallback:

.. code-block:: python

   binder.bind(Service).to(Legacy).for_python_version("<3.11")
   binder.bind(Service).to(Modern).for_python_version(">=3.11")
   binder.bind(Service).to(Fallback)  # after conditionals

Do **not** put the fallback first. ``bind(Service).to(Fallback)`` followed
by ``bind(Service).to(Modern).for_python_version(...)`` loses Fallback:
``.to(Modern)`` last-wins into the ordinary registration map, then
``for_version`` retracts that registration into the candidate list, leaving
no unconditional binding. The same footgun applies if you
``self.register(Service, Fallback)`` before a version-conditioned
``.to(...).for_*``.

``Config.register`` after the version candidates works as a fallback, same
as a trailing ``bind(...).to(...)``.

**Providers, instances, and scopes**

- ``.to_provider(...)`` / ``.to_instance(...)`` may appear before
  ``for_version`` / ``for_python_version`` / ``for_package_version`` /
  ``for_package_present`` / ``for_package_absent``; the winning candidate
  keeps that target shape.
- ``.in_scope(...)`` on a version-conditioned chain applies to that
  candidate. A scoped unconditional fallback is only used when no
  candidate matches.
- Unrelated types are unaffected: version selection for ``Service`` does
  not clear or change bindings for ``Other``.

**install and override**

- ``install`` **extends** the candidate list (and merges version sources /
  named parsers). Hosts can add more ``for_*`` alternatives or a trailing
  unconditional fallback.
- ``override(base).with_(test)`` also extends candidates. Unconditional
  bindings still last-wins: a test module's ``bind(Service).to(Fake)``
  replaces the base fallback when no version candidate matches.
- ``for_python_version`` does **not** eagerly bind
  :class:`~pyiv.version.SysPythonVersionProvider` during ``configure``.
  A default Sys binding is installed only after merge, and only if no
  ``PythonVersionProvider`` is already present. That way a base
  :class:`~pyiv.version.FixedPythonVersionProvider` survives an override
  module that only adds more ``for_python_version`` candidates.
- At selection time, every :class:`~pyiv.version.PythonVersionSource` is
  rebound to the **merged** config so it sees the final
  ``PythonVersionProvider`` (not a submodule's empty graph).

Package versions
----------------

``for_package_version(distribution, specifier)`` reads
``importlib.metadata.version(distribution)``. Pass the **distribution**
name (as on PyPI), which may differ from the import package name. Tests
should register a :class:`~pyiv.version.MapVersionSource` for
``package:<distribution>`` (see :func:`~pyiv.version.package_version_domain`)
instead of installing multiple package versions.

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.version import MapVersionSource, package_version_domain

   class HttpClient:
       name = "base"

   class Legacy(HttpClient):
       name = "legacy"

   class Modern(HttpClient):
       name = "modern"

   domain = package_version_domain("requests")

   class HttpConfig(Config):
       def configure(self):
           b = self.get_binder()
           b.version_source(domain, MapVersionSource({domain: "2.31.0"}))
           b.bind(HttpClient).to(Legacy).for_package_version("requests", "<2.30")
           b.bind(HttpClient).to(Modern).for_package_version(
               "requests", ">=2.30,<3"
           )

   assert get_injector(HttpConfig).inject(HttpClient).name == "modern"

When you only care about install vs missing (not a version range), use
``for_package_present`` / ``for_package_absent`` below instead of inventing
a catch-all PEP 440 specifier.

.. _package-presence-absence:

Package presence / absence (optional accelerators)
--------------------------------------------------

When you only care whether a distribution is **installed** (not which
version), use ``for_package_present`` and/or ``for_package_absent``.

**Explicit both sides** (no unconditional fallback needed — exactly one
matches):

.. code-block:: python

   from pyiv import Config, get_injector

   class Encoder:
       kind = "base"

   class CJsonEncoder(Encoder):
       kind = "cjson"

   class JsonEncoder(Encoder):
       kind = "json"

   class EncoderConfig(Config):
       def configure(self):
           binder = self.get_binder()
           binder.bind(Encoder).to(CJsonEncoder).for_package_present("cjson")
           binder.bind(Encoder).to(JsonEncoder).for_package_absent("cjson")

**Presence + unconditional fallback** (same outcome when the package is
missing; register the fallback **after**):

.. code-block:: python

   binder.bind(Encoder).to(CJsonEncoder).for_package_present("cjson")
   binder.bind(Encoder).to(JsonEncoder)  # fallback when cjson absent

**Testing presence without installing the package:** register a
:class:`~pyiv.version.MapVersionSource` for
``package:<distribution>`` (same as version-range tests). Omit the source
(or use a name that is not installed) to exercise the absent path.

.. code-block:: python

   from pyiv.version import MapVersionSource, package_version_domain

   domain = package_version_domain("cjson")
   binder.version_source(domain, MapVersionSource({domain: "1.0.0"}))
   binder.bind(Encoder).to(CJsonEncoder).for_package_present("cjson")
   binder.bind(Encoder).to(JsonEncoder).for_package_absent("cjson")

``for_package_present`` / ``for_package_absent`` are sugar for
``for_package_version(distribution, \"*\")`` /
``for_package_version(distribution, \"!\")``
(:data:`~pyiv.version.PACKAGE_PRESENT` /
:data:`~pyiv.version.PACKAGE_ABSENT`). This checks **distribution
metadata**, not whether the import package is already loaded in
``sys.modules``.
