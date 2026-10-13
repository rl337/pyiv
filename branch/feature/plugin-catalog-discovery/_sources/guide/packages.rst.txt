Packages
========

Core ``pyiv`` is the Python standard library only. Third-party integrations
live in extra packages. Prefer **one** extra (``pyiv-common``) over a
package per library.

Three tiers
-----------

**``pyiv`` (core).** Runtime depends on the standard library. Encoder and
network *infrastructure* (``SerDe``, ``NetworkClient``) and stdlib
implementations (JSON, Base64, XML, Pickle, urllib HTTP/HTTPS) stay here.

**``pyiv-common``.** Ubiquitous libraries that are the ``#include <stdlib.h>``
of Python. Today that is PyYAML and requests. Install it when you need YAML
or the requests HTTP stack.

**Dedicated extras.** Domain-specific stacks (PostgreSQL, AWS, Redis) would
be ``pyiv-<domain>`` packages — for example a future ``pyiv-pgsql``. Do not
create those unless the dependency would pollute ``pyiv-common``. The
``PostgreSQL(Database)`` class in the quick start is a DI teaching example,
not a driver.

Install
-------

.. code-block:: bash

   pip install pyiv
   pip install pyiv-common

``pip install pyiv[common]`` is equivalent to installing ``pyiv-common``.
Unreleased extra from this repo:

.. code-block:: bash

   pip install "pyiv-common @ git+https://github.com/rl337/pyiv.git#subdirectory=extras/pyiv-common"

YAML
----

.. code-block:: python

   from pyiv import ChainType, Config, get_injector
   from pyiv_common.serde import YAMLSerDe

   class MyConfig(Config):
       def configure(self):
           self.register_chain_handler(ChainType.ENCODING, "yaml", YAMLSerDe)

   injector = get_injector(MyConfig)
   serde = injector.inject_chain_handler(ChainType.ENCODING, "yaml")
   serde.deserialize(serde.serialize({"key": "value"}))

``from pyiv.serde import YAMLSerDe`` still works if ``pyiv-common`` is
installed (compatibility shim). Prefer ``pyiv_common.serde``.

requests HTTP
-------------

.. code-block:: python

   from pyiv import ChainType, Config, get_injector
   from pyiv_common.network import RequestsClient

   class MyConfig(Config):
       def configure(self):
           self.register_chain_handler(
               ChainType.NETWORK_CLIENT, "http", RequestsClient
           )

   injector = get_injector(MyConfig)
   client = injector.inject_chain_handler(ChainType.NETWORK_CLIENT, "http")

Core still ships urllib ``HTTPClient`` / ``HTTPSClient`` with no extra
dependencies. See :doc:`/pyiv_common/pyiv_common`.
