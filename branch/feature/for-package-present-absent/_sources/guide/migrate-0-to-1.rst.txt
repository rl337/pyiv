Migrating from pyiv 0.x to 1.x
=============================

pyiv **1.0** replaces the chain-based ``NetworkClient`` HTTP surface with
typed ``HttpClient`` / ``AsyncHttpClient`` interfaces. There is no
deprecation shim: upgrade call sites when you move to 1.x. The ``0.x``
maintenance branch remains available for patch releases of the old API.

HTTP clients
------------

**Removed**

* ``pyiv.network`` (``NetworkClient``, ``HTTPClient``, ``HTTPSClient``)
* ``ChainType.NETWORK_CLIENT`` and chain registration for HTTP
* Dict responses (``{"status", "headers", "body", "url"}``)
* ``NetworkClient.handle()`` tuple / dict / bare-URL dispatch

**Use instead**

* Depend on :class:`~pyiv.http.base.HttpClient` or
  :class:`~pyiv.http.base.AsyncHttpClient`
* Bind :class:`~pyiv.http.clients.UrllibHttpClient` (stdlib) or
  :class:`~pyiv_common.network.RequestsHttpClient` (requests extra)
* In tests, bind :class:`~pyiv.http.memory.MemoryHttpClient` /
  :class:`~pyiv.http.memory.MemoryAsyncHttpClient`

0.x style::

   from pyiv import ChainType, Config, get_injector
   from pyiv.network import HTTPClient

   class MyConfig(Config):
       def configure(self):
           self.register_chain_handler(ChainType.NETWORK_CLIENT, "http", HTTPClient)

   client = get_injector(MyConfig).inject_chain_handler(
       ChainType.NETWORK_CLIENT, "http"
   )
   result = client.request("GET", "https://example.com/")
   body = result["body"]

1.x style::

   from pyiv import Config, get_injector
   from pyiv.http import HttpClient, UrllibHttpClient

   class MyConfig(Config):
       def configure(self):
           self.register(HttpClient, UrllibHttpClient)

   client = get_injector(MyConfig).inject(HttpClient)
   response = client.get("https://example.com/")
   body = response.content
   response.raise_for_status()

``pyiv-common``
---------------

* ``RequestsClient`` still exists as an alias of ``RequestsHttpClient``
* Register it as ``HttpClient``, not as a ``NETWORK_CLIENT`` chain handler
* ``pyiv-common`` 0.2+ requires ``pyiv>=1.0.0``

Install: ``pip install "pyiv>=1.0"`` and, if needed,
``pip install "pyiv-common>=0.2"``.

What did not change
-------------------

SerDe chain handlers (``ChainType.ENCODING``), Binder, scopes, keys,
version-conditioned bindings (including later ``for_package_present`` /
``for_package_absent``), and test doubles for Clock / Filesystem /
Console / DateTimeService are unchanged in spirit. Only the HTTP
integration surface was redesigned.
