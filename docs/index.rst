.. pyiv documentation master file

PyIV Documentation
==================

.. raw:: html

   <p style="font-size: 1.2em; color: #666; margin: 20px 0;">
   <span style="display: inline-block; padding: 4px 8px; background: #0066cc; color: white; border-radius: 4px; font-size: 0.85em; font-weight: 500; margin-right: 10px;">v|release|</span>
   A lightweight, type-aware dependency injection library for Python applications.
   PyIV provides a simple yet powerful way to manage dependencies, improve testability, and reduce coupling.
   </p>

   <div style="margin: 20px 0; padding: 15px; background: #e8f4f8; border-left: 4px solid #0066cc; border-radius: 4px;">
   <strong>Quick Links:</strong>
   <a href="https://github.com/rl337/pyiv" style="margin-left: 15px; color: #0066cc; text-decoration: none; font-weight: 500;">GitHub Repository</a>
   <a href="https://github.com/rl337/pyiv/blob/main/README.md" style="margin-left: 15px; color: #0066cc; text-decoration: none; font-weight: 500;">README</a>
   <a href="https://pypi.org/project/pyiv/" style="margin-left: 15px; color: #0066cc; text-decoration: none; font-weight: 500;">PyPI Package</a>
   </div>

Key Features
------------

.. raw:: html

   <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">🔧 Type-Based Resolution</h4>
   <p style="margin: 0;">Automatic dependency resolution using Python type annotations. No manual wiring required.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">🎯 Singleton Management</h4>
   <p style="margin: 0;">Built-in singleton lifecycle management (per-injector or global) for efficient resource usage.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">🏭 Factory Pattern</h4>
   <p style="margin: 0;">Factory pattern support for complex object creation with dependency injection.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">🧪 Test-Friendly</h4>
   <p style="margin: 0;">Built-in abstractions for Clock, Filesystem, and DateTimeService make testing easy.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">📦 Zero Dependencies</h4>
   <p style="margin: 0;">Pure Python implementation with no external dependencies. Lightweight and fast.</p>
   </div>
   <div style="padding: 20px; background: #f9f9f9; border-radius: 6px; border-left: 4px solid #0066cc;">
   <h4 style="margin-top: 0; color: #0066cc;">🔍 Reflection Support</h4>
   <p style="margin: 0;">Automatic discovery of interface implementations in packages using ReflectionConfig.</p>
   </div>
   </div>

Quick Start
-----------

Get started with PyIV in just a few lines of code:

.. code-block:: python

   from pyiv import Config, get_injector

   # Define your configuration
   class MyConfig(Config):
       def configure(self):
           self.register(Database, PostgreSQL)
           self.register(Logger, FileLogger, singleton=True)

   # Create injector and resolve dependencies
   injector = get_injector(MyConfig)
   db = injector.inject(Database)
   logger = injector.inject(Logger)

Installation
------------

.. code-block:: bash

   pip install pyiv

   # Or with Poetry
   poetry add pyiv

Example: Testing with Abstractions
-----------------------------------

PyIV makes testing easy with built-in abstractions:

.. code-block:: python

   from pyiv.clock import Clock, SyntheticClock
   from pyiv.filesystem import Filesystem, MemoryFilesystem
   from pyiv import Config, get_injector

   # Production config
   class ProdConfig(Config):
       def configure(self):
           self.register(Clock, RealClock)
           self.register(Filesystem, RealFilesystem)

   # Test config
   class TestConfig(Config):
       def configure(self):
           self.register(Clock, SyntheticClock, singleton=True)
           self.register(Filesystem, MemoryFilesystem)

   # Use in tests
   injector = get_injector(TestConfig)
   clock = injector.inject(Clock)
   clock.set_time(100.0)  # Control time in tests!
   filesystem = injector.inject(Filesystem)
   filesystem.write_text('test.txt', 'content')  # In-memory filesystem!

Core Modules
------------

Explore the PyIV modules to understand the full capabilities:

.. raw:: html

   <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin: 30px 0;">
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Main package - Core dependency injection framework</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-config" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.config</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Configuration base class - Register dependencies</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-injector" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.injector</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Dependency injection engine - Creates and manages instances</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-singleton" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.singleton</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Singleton lifecycle management - Per-injector or global</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-factory" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.factory</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Factory pattern support - Create objects with dependencies</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-clock" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.clock</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Time abstraction - RealClock for production, SyntheticClock for testing</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-filesystem" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.filesystem</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">File I/O abstraction - RealFilesystem for production, MemoryFilesystem for testing</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-console" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.console</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Console output abstraction - RealConsole for production, MemoryConsole/PTYConsole/MockConsole for testing</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-datetime-service" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.datetime_service</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">DateTime abstraction - PythonDateTimeService for production, MockDateTimeService for testing</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-reflection" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.reflection</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Reflection-based discovery - Automatically find implementations</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-command" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.command</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Command interface - Build CLI applications with dependency injection</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-chain" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.chain</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Chain of responsibility pattern - Extensible handler system for encoding, hashing, sorting, network clients</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-serde" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.serde</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Serialization/deserialization - JSON, Base64, XML, YAML, Pickle, and more</div>
   </a>
   </div>
   <div style="padding: 15px; background: #f9f9f9; border-radius: 6px; border: 1px solid #e0e0e0; transition: all 0.2s;">
   <a href="modules.html#pyiv-network" style="color: #0066cc; text-decoration: none; font-weight: 500; display: block;">
   <div style="font-family: 'Monaco', 'Courier New', monospace; color: #333; font-size: 0.95em;">pyiv.network</div>
   <div style="color: #666; font-size: 0.85em; margin-top: 5px;">Network clients - HTTP, HTTPS, and other protocol clients with dependency injection</div>
   </a>
   </div>
   </div>

API Documentation
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Complete API Reference

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

