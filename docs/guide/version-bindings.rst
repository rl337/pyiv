Version-conditioned bindings
============================

Select among several implementations of the same interface based on a
**named version domain** — the running Python interpreter, an installed
distribution, or any host-defined domain (OS release, wire protocol, …).

See :mod:`pyiv.version` for the full API (sources, comparers, candidates).
This page is the how-to.

Fluent API
----------

``for_python_version`` and ``for_package_version`` are convenience adapters
over ``for_version``. They use :pep:`440` matching via
:class:`~pyiv.version.Pep440VersionComparer`.

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

Custom domains
--------------

Register a :class:`~pyiv.version.VersionSource` for the domain. Optionally
register a custom :class:`~pyiv.version.VersionComparer` when versions are
not PEP 440 (for example an OS release string). The comparer exposes
``is_version_compatible``, ``is_version_less``, and ``is_version_greater``.

.. code-block:: python

   from pyiv import Config, get_injector
   from pyiv.version import MapVersionSource

   class FsTool:
       name = "base"

   class AlpineFs(FsTool):
       name = "alpine"

   class AlpineComparer:
       def is_version_compatible(self, version, specifier):
           assert specifier.startswith(">=")
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
           binder.version_source("alpine", MapVersionSource({"alpine": "3.19.0"}))
           binder.version_comparer("alpine", AlpineComparer())
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

Package versions
----------------

``for_package_version(distribution, specifier)`` reads
``importlib.metadata.version(distribution)``. Pass the **distribution**
name (as on PyPI), which may differ from the import package name. Tests
should register a :class:`~pyiv.version.MapVersionSource` for
``package:<distribution>`` (see :func:`~pyiv.version.package_version_domain`)
instead of installing multiple package versions.
