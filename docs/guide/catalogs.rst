Catalogs without registries
===========================

Hosts often keep a hand-rolled ``*Registry`` map for plugins, recipes, or
tools. Prefer a **map multibind** (or ``Named`` keys) as the only membership
source, then expose a thin facade for ``names`` / ``get`` / ``describe``.

See also :doc:`keys` (Named vs multibinder) and :doc:`binding` (``install`` /
merge). Design background:
:doc:`../inspiration/plugin-catalog-discovery-inspiration`.

Register the catalog
--------------------

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

List without constructing
-------------------------

CLI ``recipes list`` should not build network clients or model backends.
``Injector.catalog_keys`` reads map-multibind membership without calling
``inject``:

.. code-block:: python

   keys = injector.catalog_keys(Recipe)
   # ['harness_run', 'verify_repair']

For ``Named`` catalogs, use ``injector.named_keys(Recipe)``.

Thin facade
-----------

Membership stays in the multibind. A facade is query API only:

.. code-block:: python

   from pyiv import Injector


   class _RecipeMap:
       def __init__(self, recipes: Dict[str, Recipe]):
           self.recipes = recipes


   class RecipeCatalog:
       def __init__(self, injector: Injector):
           self._injector = injector

       def names(self):
           return self._injector.catalog_keys(Recipe)

       def get(self, name: str):
           return self._injector.inject(_RecipeMap).recipes[name]

       def describe(self, name: str) -> dict:
           recipe = self.get(name)
           return {"name": recipe.name, "type": type(recipe).__name__}


   class AppConfig(CatalogConfig):
       def configure(self):
           super().configure()
           self.register(RecipeCatalog, RecipeCatalog)

``names()`` stays cheap. ``get()`` builds the map when instances are needed.

Host extension with conflict policy
-----------------------------------

``install`` merges map keys (later wins by default). Prefer
``contribute_map`` when a host must state the conflict rule:

.. code-block:: python

   class LibraryConfig(Config):
       def configure(self):
           self.contribute_map(Recipe, "harness_run", HarnessRun)
           self.contribute_map(Recipe, "verify_repair", VerifyRepair)


   class HostConfig(Config):
       def configure(self):
           self.install(LibraryConfig)
           self.contribute_map(
               Recipe, "acme.widget_loop", WidgetLoop, on_conflict="error"
           )

``on_conflict`` is ``"replace"`` (default), ``"error"``, or ``"keep"``.
``contribute_map_entries`` accepts a whole mapping with the same policy.

Reflection into a multibind
---------------------------

``ReflectionConfig.register_module`` defaults to unqualified ``register``
(last wins). For catalogs, opt in:

.. code-block:: python

   from pyiv.reflection import ReflectionConfig


   class PluginConfig(ReflectionConfig):
       def configure(self):
           self.register_module(
               Recipe,
               "myapp.recipes",
               pattern="*Template",
               as_multibind="map",
               key_attr="name",
           )

Discovered classes join the map multibind via ``key_attr``. Duplicate keys
use ``on_conflict`` (default ``"error"``). Unqualified ``inject(Recipe)``
stays unbound unless you register a default separately.
