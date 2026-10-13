Plugin catalog discovery (inspiration)
======================================

**Status:** inspiration / design ask — not a committed roadmap or API contract.

**Audience:** pyiv maintainers and host libraries (e.g. MechaHarness) that want
**zero hand-rolled registries** and a single DI-owned catalog for plugins,
recipes, runners, and similar open-string identities.

**Provenance:** MechaHarness wants Agentic Recipes (``GraphTemplate`` subclasses),
node runners, tools, and context providers bound only through pyiv — not a
parallel ``*Registry`` map that hosts must merge by hand. This note captures the
gaps that currently push libraries to keep those maps.

Problem
-------

Hosts want:

1. **One membership source** — the injector (Named keys and/or map multibinds).
2. **Discovery without a second store** — CLI / docs / “list plugins” read the
   same bindings production inject uses.
3. **Host merge without forking** — subclass Config (or ``install`` a module) and
   *add* catalog entries; do not replace the library catalog wholesale.
4. **Ctor injection of catalog members** — plugins can take ``Completer``,
   ``Clock``, etc.; they are real injectables, not zero-arg data bags.

Today pyiv already has most of the *registration* story (``Named`` / ``Matched``,
``map_multibinder``, ``List``/``Set`` multibinder, ``ReflectionConfig``, Config
``install`` / ``merge_from``). What is missing is a crisp **catalog / discovery**
story so libraries stop wrapping those bindings in hand-rolled registries.

Desired outcomes (examples)
---------------------------

1. List bound catalog keys without injecting every plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Dict

   from pyiv import Config, get_injector


   class Recipe:
       name: str = "recipe"


   class HarnessRun(Recipe):
       name = "harness_run"


   class VerifyRepair(Recipe):
       name = "verify_repair"


   class CatalogConfig(Config):
       def configure(self):
           mb = self.map_multibinder(Recipe)
           mb.add("harness_run", HarnessRun)
           mb.add("verify_repair", VerifyRepair)


   injector = get_injector(CatalogConfig)

   # Desired (additive API sketch):
   keys = injector.catalog_keys(Recipe)          # ["harness_run", "verify_repair"]
   named = injector.named_keys(Recipe)           # Named qualifiers for Recipe
   meta = injector.catalog_entries(Recipe)       # key -> Provider / binding kind

   # Still works today for *runtime* use:
   class RecipeHost:
       def __init__(self, recipes: Dict[str, Recipe]):
           self.recipes = recipes

   host = injector.inject(RecipeHost)
   assert set(host.recipes) == set(keys)

**Why:** CLI ``recipes list`` / host consoles need names and summaries *before*
constructing heavy plugins (network clients, model backends). Forcing
``inject(Dict[str, Recipe])`` eagerly constructs everything and couples listing
to construction success.

Also for Named catalogs:

.. code-block:: python

   from pyiv.key import Key, Named

   # After register_key(Key(Recipe, Named(["harness_run"])), HarnessRun), …
   keys = injector.named_keys(Recipe)
   # -> iterable of Named qualifiers (or tag frozensets) bound for Recipe

2. Thin injectable facade (no second ownership)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Dict

   class RecipeCatalog:
       """Query API only — membership lives in the map multibind."""

       def __init__(self, recipes: Dict[str, Recipe]):
           self._recipes = recipes

       def names(self) -> list:
           return sorted(self._recipes)

       def get(self, name: str):
           return self._recipes.get(name)

       def describe(self, name: str) -> dict:
           recipe = self._recipes[name]
           return {"name": recipe.name, "type": type(recipe).__name__}


   class AppConfig(CatalogConfig):
       def configure(self):
           super().configure()
           self.register(RecipeCatalog, RecipeCatalog)  # ctor gets Dict[str, Recipe]

With **catalog_keys** (gap 1), ``RecipeCatalog`` can take
``Provider[Dict[str, Recipe]]`` or a binding inspector and defer construction
until ``get()``.

3. Host merge that *extends* the catalog
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``merge_from`` already unions map-multibind keys (later wins when
``replace=True``). Hosts still need a **documented, intentional** contrib API:

.. code-block:: python

   class LibraryConfig(Config):
       def configure(self):
           mb = self.map_multibinder(Recipe)
           mb.add("harness_run", HarnessRun)
           mb.add("verify_repair", VerifyRepair)


   class HostConfig(Config):
       def configure(self):
           self.install(LibraryConfig)
           # Desired: explicit contrib that documents conflict policy
           self.contribute_map(Recipe, "acme.widget_loop", WidgetLoop)
           # or:
           self.map_multibinder(Recipe).add("acme.widget_loop", WidgetLoop)

**Desired clarifications / helpers:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Situation
     - Desired behavior
   * - Host adds a **new** key
     - Accept
   * - Host rebinds an **existing** key
     - Opt-in overwrite *or* raise with both types named
   * - Library ``install``\ s two modules that both bind ``"verify_repair"``
     - Same policy as above; never silently drop one without a rule
   * - List multibind order across ``install``
     - Document: library order then host appends (today: ``extend``)

Optional sugar:

.. code-block:: python

   # Desired
   self.contribute_map(
       Recipe,
       {"acme.widget_loop": WidgetLoop},
       on_conflict="error",  # or "replace" / "keep"
   )

4. Reflection that fills a multibind, not last-wins ``register``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Today ``ReflectionConfig.register_module(Handler, "pkg.handlers")`` ends in
``register(interface, impl_class)`` per discovery — **last implementation wins**
for unqualified inject. That is wrong for catalogs.

.. code-block:: python

   from pyiv.reflection import ReflectionConfig


   class PluginConfig(ReflectionConfig):
       def configure(self):
           # Desired opt-in (sketch):
           self.register_module(
               Recipe,
               "myapp.recipes",
               pattern="*Template",
               as_multibind="map",          # "set" | "list" | "map" | None (legacy)
               key_attr="name",            # class attr or callable for map keys
               singleton_type=...,
           )

Effect when ``as_multibind="map"``:

- Each discovered class → ``map_multibinder(Recipe).add(getattr(cls, "name"), cls)``
- Duplicate keys → configurable conflict policy
- Unqualified ``inject(Recipe)`` remains unbound unless ``default=`` / separate binding

When ``as_multibind="list"`` / ``"set"``: append/union into the existing multibind
so ``install`` of several scanned packages accumulates plugins.

5. Optional: inject collections without a host class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Today collections must be constructor params of a host type (documented). A
catalog-oriented API could allow:

.. code-block:: python

   # Desired optional sugar (lower priority than catalog_keys):
   recipes = injector.inject_map(Recipe)   # Dict[str, Recipe]
   handlers = injector.inject_set(Handler)

Keep the host-constructor path as the primary teaching example; sugar must not
break typing clarity.

Gap summary
-----------

.. list-table::
   :header-rows: 1
   :widths: 10 22 28 40

   * - ID
     - Gap
     - Today
     - Ask
   * - **PC-01**
     - Introspect catalog membership
     - Must inject ``Dict``/``Set``/``List`` via a host (eager)
     - ``catalog_keys`` / ``named_keys`` / binding metadata without constructing
   * - **PC-02**
     - Named catalog listing
     - No public “all Named qualifiers for type T”
     - Symmetric to map keys for ``Key(T, Named(...))``
   * - **PC-03**
     - Contrib / conflict policy
     - Map merge last-wins on ``replace=True``; easy to misuse
     - Explicit ``contribute_*`` + ``on_conflict=``
   * - **PC-04**
     - Reflection → multibind
     - Reflection overwrites unqualified binding
     - Opt-in ``as_multibind`` + ``key_attr``
   * - **PC-05**
     - Docs: “registry = DI”
     - Guide shows multibind but not catalog facades
     - Guide section: replace hand-rolled registries
   * - **PC-06**
     - Lazy catalog get
     - N/A
     - Document ``Provider[Dict[str, T]]`` / per-key ``Provider`` patterns for facades

Backward compatibility
----------------------

Principles: **additive first**; change defaults only with a major bump or an
explicit opt-in flag.

Keep unchanged (default)
~~~~~~~~~~~~~~~~~~~~~~~~

- ``map_multibinder`` / ``multibinder`` registration and inject-via-host-constructor.
- ``merge_from`` union semantics for map and list/set multibinds.
- ``Named`` / ``Matched`` inject rules and default uniqueness.
- ``ReflectionConfig.register_module(...)`` **without** new kwargs continues to
  call ``register(interface, impl)`` (last wins) — existing apps keep working.

Additive APIs (minor / compatible)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **``Injector.catalog_keys(value_type) -> list``**
   Keys from map multibindings (impl + instance maps), sorted or insertion
   order documented. Empty list if none. Does not construct values.

2. **``Injector.named_keys(abstract_type) -> list[Named]``** (or tag frozensets)
   Qualifiers registered for that type. Does not construct.

3. **``Injector.binding_info(abstract_type | Key) -> …``**
   Optional richer inspector for tools/CLI (provider kind, singleton, source
   module if known). Start small; expand later.

4. **``Config.contribute_map(value_type, key, impl, *, on_conflict=...)``**
   Thin wrapper over ``map_multibinder`` with explicit conflict policy.
   Default ``on_conflict="replace"`` matches today’s merge; ``"error"`` for strict
   catalogs.

5. **``ReflectionConfig.register_module(..., as_multibind=None, key_attr=None)``**

   - ``as_multibind is None`` → legacy ``register`` behavior.
   - ``"map"`` / ``"set"`` / ``"list"`` → multibind path only (does **not** also
     overwrite unqualified ``register`` unless ``also_default=True``).

6. Guide page (or keys.rst section) **“Catalogs without registries”** with the
   facade example above.

Compatibility matrix
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Change
     - Release
     - Migration
   * - ``catalog_keys`` / ``named_keys``
     - Minor
     - None
   * - ``contribute_map(..., on_conflict=)``
     - Minor
     - None; default = current replace
   * - Reflection ``as_multibind=``
     - Minor
     - Opt-in; omit → legacy
   * - Change Reflection **default** to multibind
     - **Major**
     - Call sites set ``as_multibind=None`` or keep explicit ``register``
   * - Eager vs lazy map inject semantics
     - Do not change
     - Facades use Provider if they need lazy

Deprecation path (if libraries adopt catalogs)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Ship PC-01/02/04 behind additive APIs; document facade pattern.
2. Host libraries (MechaHarness) migrate off hand-rolled ``*Registry`` types to
   ``Dict[str, T]`` + optional facade class.
3. Only if Reflection’s last-wins default becomes a footgun in practice:
   deprecate unqualified multi-``register`` from ``register_module`` in a major
   version, with a clear warning when a second impl is discovered.

What not to do
~~~~~~~~~~~~~~

- Do not require a central string enum of plugin names inside pyiv.
- Do not add a second “PluginRegistry” type in pyiv that reintroduces
  hand-rolled membership.
- Do not break Guice-style “one unqualified binding per type” for non-catalog
  use cases.

Suggested implementation order
------------------------------

1. **PC-01 + PC-02** — introspection unlocks CLI/docs without design churn.
2. **PC-05** — document facade + map multibind as the registry replacement.
3. **PC-03** — ``contribute_map`` / conflict policy sugar.
4. **PC-04** — Reflection opt-in multibind (largest behavior surface).
5. **PC-06** — Provider/lazy examples once facades exist in the wild.

Success criteria
----------------

A host library can:

- Bind plugins only with ``map_multibinder`` / ``Named`` (plus Config ``install``).
- List catalog ids for a CLI **without** constructing plugins.
- Inject a thin facade that answers ``get`` / ``describe``.
- Extend the catalog from a subclass without maintaining a parallel
  ``default_*()`` list in application code.
- Optionally scan a package into that same multibind via Reflection without
  last-wins loss.

When those hold, hand-rolled registries become unnecessary wrappers rather
than the source of truth.

Related pyiv surfaces
---------------------

- :doc:`../guide/catalogs` — catalogs without registries (normative guide)
- :doc:`../guide/keys` — Named / Matched vs multibinder
- :doc:`../pyiv/pyiv.multibinder`
- :doc:`../pyiv/pyiv.reflection`
- :doc:`../guide/binding` — ``install`` / merge

Related external context
------------------------

MechaHarness (consumer): retiring ``GraphTemplateRegistry``,
``GraphNodeRunnerRegistry``, ``ToolRegistry``, ``ContextProviderRegistry``, and
similar maps in favor of pyiv catalog bindings + injectable facades.
