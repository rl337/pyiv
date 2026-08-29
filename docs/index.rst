.. pyiv documentation master file

PyIV Documentation
==================

A Guice-style dependency injection library for Python. Register bindings,
inject by type, and swap production implementations for test doubles without
mocking the world.

.. container:: hero-meta

   .. container:: version-badge

      |release|

   Zero runtime dependencies. Python 3.8+.

.. raw:: html

   <div style="margin: 20px 0; padding: 15px; background: #e8f4f8; border-left: 4px solid #0066cc; border-radius: 4px;">
   <strong>Quick Links:</strong>
   <a href="https://github.com/rl337/pyiv" style="margin-left: 15px; color: #0066cc; text-decoration: none; font-weight: 500;">GitHub</a>
   <a href="changelog.html" style="margin-left: 15px; color: #0066cc; text-decoration: none; font-weight: 500;">Changelog</a>
   <a href="https://github.com/rl337/pyiv/blob/main/README.md" style="margin-left: 15px; color: #0066cc; text-decoration: none; font-weight: 500;">README</a>
   </div>

Key Features
------------

.. raw:: html

   <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">Type-based injection</h4>
   <p style="margin: 0;">Constructor injection from type annotations. Register an interface once; the injector builds the graph.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">Scopes</h4>
   <p style="margin: 0;">Per-injector and process-wide singletons, plus an extensible Scope API for custom lifecycles.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">Keys and Binder</h4>
   <p style="margin: 0;">Named/qualified bindings for multiple implementations of one type, and a fluent Binder API.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">Reflection</h4>
   <p style="margin: 0;">Discover interface implementations in a package instead of listing every class by hand.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">Test doubles</h4>
   <p style="margin: 0;">Clock, Filesystem, Console, and DateTimeService ship with in-memory implementations for tests.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">Zero dependencies</h4>
   <p style="margin: 0;">Runtime is the Python standard library only. No extra packages to pin or audit.</p>
   </div>
   </div>

Installation
------------

PyIV is not on PyPI yet. Install from GitHub:

.. code-block:: bash

   pip install git+https://github.com/rl337/pyiv.git

Requires Python 3.8 or newer.

Quick Start
-----------

.. code-block:: python

   from pyiv import Config, get_injector

   class Database:
       pass

   class PostgreSQL(Database):
       pass

   class Logger:
       pass

   class FileLogger(Logger):
       pass

   class MyConfig(Config):
       def configure(self):
           self.register(Database, PostgreSQL)
           self.register(Logger, FileLogger, singleton=True)

   injector = get_injector(MyConfig)
   db = injector.inject(Database)       # PostgreSQL
   logger = injector.inject(Logger)     # shared per injector

User Guide
----------

Binder vs ``register``, scopes, qualified keys, and swapping Clock /
Filesystem / Console / DateTimeService in tests:

.. toctree::
   :maxdepth: 1
   :caption: User guide

   Binding <guide/binding>
   Scopes <guide/scopes>
   Keys and collections <guide/keys>
   Testing with doubles <guide/testing>

API Reference
-------------

The left navigation lists every public module. Pages are generated from
docstrings in the ``pyiv`` package; doctests in those docstrings are run in CI.

.. toctree::
   :maxdepth: 1
   :caption: Core DI

   pyiv/pyiv
   pyiv/pyiv.config
   pyiv/pyiv.injector
   pyiv/pyiv.binder
   pyiv/pyiv.key
   pyiv/pyiv.scope
   pyiv/pyiv.provider
   pyiv/pyiv.singleton

.. toctree::
   :maxdepth: 1
   :caption: Bindings

   pyiv/pyiv.optional
   pyiv/pyiv.multibinder
   pyiv/pyiv.members
   pyiv/pyiv.factory

.. toctree::
   :maxdepth: 1
   :caption: Discovery

   pyiv/pyiv.reflection
   pyiv/pyiv.chain
   pyiv/pyiv.command

.. toctree::
   :maxdepth: 1
   :caption: Test doubles

   pyiv/pyiv.clock
   pyiv/pyiv.filesystem
   pyiv/pyiv.console
   pyiv/pyiv.datetime_service

.. toctree::
   :maxdepth: 1
   :caption: Integrations

   pyiv/pyiv.serde
   pyiv/pyiv.network

.. toctree::
   :maxdepth: 1
   :caption: Reference

   changelog
   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
