Hierarchy and private modules
=============================

Child injectors and private configs isolate bindings the way Guice child
injectors and private modules do, with Python ``Config`` APIs.

Child injectors
---------------

``create_child`` builds an injector that inherits parent bindings. The parent
cannot see child bindings. Use a child for request/session overlays.

.. code-block:: python

   from pyiv import Config, get_injector

   class Database:
       pass

   class ProdConfig(Config):
       def configure(self):
           self.register(Database, Database)

   class RequestId:
       def __init__(self, value: str = "r1"):
           self.value = value

   class RequestConfig(Config):
       def configure(self):
           self.register(RequestId, RequestId)

   root = get_injector(ProdConfig)
   child = root.create_child(RequestConfig)
   child.inject(Database)   # from parent
   child.inject(RequestId)  # from child

Private modules
---------------

``PrivateConfig`` bindings are hidden unless ``expose``-d. Installing a
private module into a parent wires a child environment; exposed types are
available on the parent as providers that delegate into that child.

.. code-block:: python

   from pyiv import Config, PrivateConfig, get_injector

   class Hidden:
       pass

   class Service:
       def __init__(self, hidden: Hidden):
           self.hidden = hidden

   class Impl(PrivateConfig):
       def configure(self):
           self.register(Hidden, Hidden)
           self.register(Service, Service)
           self.expose(Service)

   class App(Config):
       def configure(self):
           self.install(Impl)

   get_injector(App).inject(Service)  # works; Hidden stays private

Explicit bindings
-----------------

``require_explicit_bindings()`` disables just-in-time construction of
unregistered concrete types. Useful with private modules so hidden concretes
are not accidentally JIT-built in the parent.

See also :doc:`binding` and :doc:`/pyiv/pyiv.config`.
