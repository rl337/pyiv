"""Tests for Guice-core parity features (0.4.0)."""

from abc import ABC, abstractmethod
from typing import Dict

import pytest

from pyiv import Config, CreationError, PrivateConfig, Stage, get_injector, override
from pyiv.key import Key, Named
from pyiv.scope import SingletonScope


class Database(ABC):
    @abstractmethod
    def name(self) -> str:
        pass


class PostgreSQL(Database):
    def name(self) -> str:
        return "postgresql"


class FakeDatabase(Database):
    def name(self) -> str:
        return "fake"


class Encoder:
    def encode(self, data: str) -> str:
        return data


class JsonEncoder(Encoder):
    def encode(self, data: str) -> str:
        return f"json:{data}"


class XmlEncoder(Encoder):
    def encode(self, data: str) -> str:
        return f"xml:{data}"


def test_install_merges_configs():
    class DbConfig(Config):
        def configure(self):
            self.register(Database, PostgreSQL)

    class AppConfig(Config):
        def configure(self):
            self.install(DbConfig)

    assert get_injector(AppConfig).inject(Database).name() == "postgresql"


def test_install_last_wins():
    class First(Config):
        def configure(self):
            self.register(Database, PostgreSQL)

    class Second(Config):
        def configure(self):
            self.register(Database, FakeDatabase)

    class App(Config):
        def configure(self):
            self.install(First)
            self.install(Second)

    assert get_injector(App).inject(Database).name() == "fake"


def test_map_multibinder():
    class Host:
        def __init__(self, encoders: Dict[str, Encoder]):
            self.encoders = encoders

    class MyConfig(Config):
        def configure(self):
            mb = self.map_multibinder(Encoder)
            mb.add("json", JsonEncoder)
            mb.add("xml", XmlEncoder)

    encoders = get_injector(MyConfig).inject(Host).encoders
    assert sorted(encoders.keys()) == ["json", "xml"]
    assert encoders["json"].encode("x") == "json:x"


def test_override_replaces_bindings():
    class Prod(Config):
        def configure(self):
            self.register(Database, PostgreSQL)

    class Test(Config):
        def configure(self):
            self.register(Database, FakeDatabase)

    inj = get_injector(override(Prod).with_(Test))
    assert inj.inject(Database).name() == "fake"


def test_stage_production_eager_singleton():
    created = []

    class Service:
        def __init__(self):
            created.append(1)

    class MyConfig(Config):
        def configure(self):
            self.get_binder().bind(Service).to(Service).in_scope(SingletonScope())

    get_injector(MyConfig, stage=Stage.PRODUCTION)
    assert created == [1]


def test_stage_production_aggregates_errors():
    class Broken(ABC):
        @abstractmethod
        def f(self) -> None:
            pass

    class MyConfig(Config):
        def configure(self):
            self.register(Broken, Broken, singleton=True)

    with pytest.raises(CreationError, match="eager singleton"):
        get_injector(MyConfig, stage=Stage.PRODUCTION)


def test_create_child_inherits_parent():
    class Root(Config):
        def configure(self):
            self.register(Database, PostgreSQL)

    class RequestId:
        def __init__(self, value: str = "r1"):
            self.value = value

    class ChildConfig(Config):
        def configure(self):
            self.register_instance(RequestId, RequestId("child"))

    root = get_injector(Root)
    child = root.create_child(ChildConfig)
    assert child.inject(Database).name() == "postgresql"
    assert child.inject(RequestId).value == "child"
    # Parent does not see the child's binding; JIT would be a different instance
    # if RequestId were requested. With an instance-only child binding, parent
    # has no registration and may still JIT a fresh RequestId — distinct object.
    parent_id = root.inject(RequestId)
    assert parent_id.value == "r1"
    assert parent_id is not child.inject(RequestId)


def test_private_config_expose():
    class Hidden:
        def __init__(self):
            self.token = "private"

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
            self.require_explicit_bindings()

    inj = get_injector(App)
    svc = inj.inject(Service)
    assert isinstance(svc.hidden, Hidden)
    assert svc.hidden.token == "private"
    # Hidden is not exposed; with explicit bindings the parent cannot resolve it
    with pytest.raises(CreationError, match="explicit binding"):
        inj.inject(Hidden)


def test_require_explicit_bindings():
    class Concrete:
        pass

    class MyConfig(Config):
        def configure(self):
            self.require_explicit_bindings()

    inj = get_injector(MyConfig)
    with pytest.raises(CreationError, match="explicit binding"):
        inj.inject(Concrete)


def test_transitive_jit_for_concrete_deps():
    class Helper:
        pass

    class Service:
        def __init__(self, helper: Helper):
            self.helper = helper

    class MyConfig(Config):
        def configure(self):
            pass

    svc = get_injector(MyConfig).inject(Service)
    assert isinstance(svc.helper, Helper)


def test_circular_dependency_reports_path():
    class Node:
        def __init__(self, child: "Node"):
            self.child = child

    # Resolve forward ref so the injector sees a real type
    Node.__init__.__annotations__["child"] = Node

    class MyConfig(Config):
        def configure(self):
            self.register(Node, Node)

    with pytest.raises(CreationError, match="Circular dependency"):
        get_injector(MyConfig).inject(Node)


def test_bind_key_fluent_registers_qualified_key():
    class MyConfig(Config):
        def configure(self):
            binder = self.get_binder()
            binder.bind_key(Key(Database, Named("primary"))).to(PostgreSQL)

    db = get_injector(MyConfig).inject(Key(Database, Named("primary")))
    assert isinstance(db, PostgreSQL)


def test_untargeted_bind_self_binding():
    class Service:
        pass

    class MyConfig(Config):
        def configure(self):
            self.get_binder().bind(Service)

    assert isinstance(get_injector(MyConfig).inject(Service), Service)


def test_inject_injector_by_type_annotation():
    from pyiv import Injector

    class Host:
        def __init__(self, container: Injector):
            self.container = container

    class MyConfig(Config):
        def configure(self):
            pass

    inj = get_injector(MyConfig)
    host = inj.inject(Host)
    assert host.container is inj


def test_creation_error_includes_path():
    class Missing(ABC):
        @abstractmethod
        def f(self) -> None:
            pass

    class Service:
        def __init__(self, missing: Missing):
            self.missing = missing

    class MyConfig(Config):
        def configure(self):
            self.register(Service, Service)

    with pytest.raises(CreationError) as excinfo:
        get_injector(MyConfig).inject(Service)
    msg = str(excinfo.value)
    assert "Service" in msg
    assert "missing" in msg.lower() or "Missing" in msg
