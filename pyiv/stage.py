"""Injector lifecycle stages (lazy vs eager singletons).

**What Problem Does This Solve?**

In development, lazy construction keeps startup fast. In production, deferred
binding errors surface only on first use. ``Stage.PRODUCTION`` eagerly creates
singleton-scoped bindings at injector build time so misconfiguration fails fast.

**Real-World Use Cases:**

- Production process boot that must fail before accepting traffic
- Local development that only builds the subgraph under test

Usage Examples:

    >>> from pyiv import Config, Stage, get_injector
    >>> from pyiv.scope import SingletonScope
    >>> class Database:
    ...     pass
    >>> class MyConfig(Config):
    ...     def configure(self):
    ...         self.get_binder().bind(Database).to(Database).in_scope(SingletonScope())
    >>> inj = get_injector(MyConfig, stage=Stage.PRODUCTION)
    >>> isinstance(inj.inject(Database), Database)
    True
"""

from enum import Enum


class Stage(Enum):
    """Injector construction stage: lazy vs fail-fast singletons.

    **Why this exists:** Lazy singletons hide binding mistakes until first use.
    Pass ``stage=Stage.PRODUCTION`` to :func:`~pyiv.injector.get_injector` so
    singleton-scoped bindings are created at boot.

    Attributes:
        DEVELOPMENT: Singletons are created lazily on first inject (default).
        PRODUCTION: Singleton-scoped bindings are created when the injector is built.

    Example:
        >>> from pyiv import Config, Stage, get_injector
        >>> from pyiv.scope import SingletonScope
        >>> class Database:
        ...     pass
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.get_binder().bind(Database).to(Database).in_scope(SingletonScope())
        >>> isinstance(get_injector(MyConfig, stage=Stage.PRODUCTION).inject(Database), Database)
        True
    """

    DEVELOPMENT = "development"
    PRODUCTION = "production"
