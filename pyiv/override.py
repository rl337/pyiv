"""Config overlay for replacing production bindings in tests.

**What Problem Does This Solve?**

Test suites need the real module graph with a few bindings swapped for doubles.
Rebuilding the whole ``Config`` is brittle. ``override(base).with_(test)``
keeps the base registrations and replaces only keys present in the override.

**Real-World Use Cases:**

- Swap ``Clock`` / ``Filesystem`` for synthetic doubles in integration tests
- Replace a remote client with an in-memory stub while keeping the rest of the graph

Usage Examples:

    >>> from pyiv import Config, get_injector
    >>> from pyiv.override import override
    >>> class Database:
    ...     def name(self) -> str:
    ...         return "prod"
    >>> class ProdDatabase(Database):
    ...     def name(self) -> str:
    ...         return "prod"
    >>> class FakeDatabase(Database):
    ...     def name(self) -> str:
    ...         return "fake"
    >>> class ProdConfig(Config):
    ...     def configure(self):
    ...         self.register(Database, ProdDatabase)
    >>> class TestConfig(Config):
    ...     def configure(self):
    ...         self.register(Database, FakeDatabase)
    >>> inj = get_injector(override(ProdConfig).with_(TestConfig))
    >>> inj.inject(Database).name()
    'fake'
"""

from typing import Tuple, Type, Union

from pyiv.config import Config


class OverrideBuilder:
    """Fluent step after :func:`override` — call :meth:`with_` to finish.

    **Why this exists:** Splitting ``override(base)`` from ``.with_(test)``
    keeps the API readable when overlaying several override modules.

    Example:
        >>> from pyiv import Config, get_injector
        >>> class Database:
        ...     def name(self) -> str:
        ...         return "prod"
        >>> class Fake(Database):
        ...     def name(self) -> str:
        ...         return "fake"
        >>> class Prod(Config):
        ...     def configure(self):
        ...         self.register(Database, Database)
        >>> class Test(Config):
        ...     def configure(self):
        ...         self.register(Database, Fake)
        >>> get_injector(override(Prod).with_(Test)).inject(Database).name()
        'fake'
    """

    def __init__(self, bases: Tuple[Union[Type[Config], Config], ...]):
        self._bases = bases

    def with_(self, *overrides: Union[Type[Config], Config]) -> Config:
        """Return a config that overlays ``overrides`` on the bases.

        Bindings in later overrides win over earlier ones and over the bases.
        """
        return OverriddenConfig(self._bases, overrides)


class OverriddenConfig(Config):
    """Merged config: base bindings with override bindings on top.

    **Why this exists:** Tests need the production graph with a few keys
    swapped. Prefer :func:`override` rather than constructing this directly.

    See the :class:`OverrideBuilder` example for usage via ``override(...).with_(...)``.
    """

    def __init__(
        self,
        bases: Tuple[Union[Type[Config], Config], ...],
        overrides: Tuple[Union[Type[Config], Config], ...],
    ):
        # Initialize empty state without running a user configure().
        self._init_stores()
        for base in bases:
            self.merge_from(_as_config(base), replace=True)
        for ov in overrides:
            self.merge_from(_as_config(ov), replace=True)

    def configure(self) -> None:
        """No-op; bindings come from merged modules."""
        pass


def override(*bases: Union[Type[Config], Config]) -> OverrideBuilder:
    """Start an override overlay over one or more base configs.

    Example::

        get_injector(override(ProdConfig).with_(TestConfig))
    """
    if not bases:
        raise ValueError("override() requires at least one base config")
    return OverrideBuilder(bases)


def _as_config(config: Union[Type[Config], Config]) -> Config:
    if isinstance(config, Config):
        return config
    if isinstance(config, type) and issubclass(config, Config):
        return config()
    raise TypeError(f"expected Config subclass or instance, got {type(config)}")
