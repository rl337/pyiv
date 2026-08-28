"""Tests for qualified Key bindings."""

import pytest

from pyiv import Config, get_injector
from pyiv.key import Key, Named


class Database:
    def __init__(self, name: str = "default"):
        self.name = name


class PostgreSQL(Database):
    def __init__(self):
        super().__init__("postgresql")


class MySQL(Database):
    def __init__(self):
        super().__init__("mysql")


def test_key_accepts_user_types():
    """Key(SomeClass) must not confuse the class with the builtin type()."""
    key = Key(Database, Named("primary"))
    assert key.type is Database
    assert key.qualifier == Named("primary")


def test_register_key_injects_implementation_class():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Database, Named("primary")), PostgreSQL)
            self.register_key(Key(Database, Named("replica")), MySQL)

    injector = get_injector(MyConfig)
    primary = injector.inject(Key(Database, Named("primary")))
    replica = injector.inject(Key(Database, Named("replica")))

    assert isinstance(primary, PostgreSQL)
    assert isinstance(replica, MySQL)
    assert primary.name == "postgresql"
    assert replica.name == "mysql"


def test_register_key_rejects_non_type_non_provider():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Database, Named("bad")), "not-a-provider")

    with pytest.raises(TypeError, match="type or Provider"):
        MyConfig()
