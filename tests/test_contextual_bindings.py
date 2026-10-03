"""Tests for when-injected-into (contextual / bound-from) bindings."""

import pytest

from pyiv import Config, get_injector
from pyiv.key import Key, Named
from pyiv.provider import Provider
from pyiv.scope import SingletonScope


class Encoder:
    def __init__(self, kind: str = "base"):
        self.kind = kind


class JSONEncoder(Encoder):
    def __init__(self):
        super().__init__("json")


class AvroEncoder(Encoder):
    def __init__(self):
        super().__init__("avro")


class AvroProducer:
    def __init__(self, encoder: Encoder):
        self.encoder = encoder


class JsonProducer:
    def __init__(self, encoder: Encoder):
        self.encoder = encoder


class LazyHost:
    def __init__(self, encoder_provider: Provider[Encoder]):
        self._provider = encoder_provider

    def get_encoder(self) -> Encoder:
        return self._provider.get()


def test_default_and_contextual_via_binder():
    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(Encoder).to(JSONEncoder)
            b.bind(Encoder).to(AvroEncoder).when_injected_into(AvroProducer)
            b.bind(AvroProducer).to(AvroProducer)
            b.bind(JsonProducer).to(JsonProducer)

    inj = get_injector(C)
    assert isinstance(inj.inject(Encoder), JSONEncoder)
    assert isinstance(inj.inject(AvroProducer).encoder, AvroEncoder)
    assert isinstance(inj.inject(JsonProducer).encoder, JSONEncoder)


def test_explicit_from_manual_inject():
    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(Encoder).to(JSONEncoder)
            b.bind(Encoder).to(AvroEncoder).when_injected_into(AvroProducer)

    inj = get_injector(C)
    assert isinstance(inj.inject(Encoder, from_=AvroProducer), AvroEncoder)
    assert isinstance(inj.inject(Encoder), JSONEncoder)


def test_explicit_from_miss_falls_back_to_default():
    class C(Config):
        def configure(self):
            self.register(Encoder, JSONEncoder)

    inj = get_injector(C)
    assert isinstance(inj.inject(Encoder, from_=AvroProducer), JSONEncoder)


def test_register_when_injected_into_preserves_default():
    class C(Config):
        def configure(self):
            self.register(Encoder, JSONEncoder)
            self.register(Encoder, AvroEncoder, when_injected_into=AvroProducer)
            self.register(AvroProducer, AvroProducer)

    inj = get_injector(C)
    assert isinstance(inj.inject(Encoder), JSONEncoder)
    assert isinstance(inj.inject(AvroProducer).encoder, AvroEncoder)


def test_register_instance_contextual():
    avro = AvroEncoder()
    json_enc = JSONEncoder()

    class C(Config):
        def configure(self):
            self.register_instance(Encoder, json_enc)
            self.register_instance(Encoder, avro, when_injected_into=AvroProducer)
            self.register(AvroProducer, AvroProducer)

    inj = get_injector(C)
    assert inj.inject(Encoder) is json_enc
    assert inj.inject(AvroProducer).encoder is avro


def test_from_not_forwarded_to_constructor():
    class NeedsKwargs:
        def __init__(self, value: str = "ok"):
            self.value = value

    class C(Config):
        def configure(self):
            self.register(NeedsKwargs, NeedsKwargs)

    inj = get_injector(C)
    # from_ must not be passed as a constructor keyword
    obj = inj.inject(NeedsKwargs, from_=AvroProducer)
    assert obj.value == "ok"


def test_subclass_owner_does_not_match():
    class SpecialAvroProducer(AvroProducer):
        pass

    class C(Config):
        def configure(self):
            self.register(Encoder, JSONEncoder)
            self.register(Encoder, AvroEncoder, when_injected_into=AvroProducer)
            self.register(SpecialAvroProducer, SpecialAvroProducer)

    inj = get_injector(C)
    # Exact match only — subclass does not see AvroProducer contextual binding
    assert isinstance(inj.inject(SpecialAvroProducer).encoder, JSONEncoder)


def test_scoped_contextual_isolated_from_default():
    class C(Config):
        def configure(self):
            b = self.get_binder()
            b.bind(Encoder).to(JSONEncoder).in_scope(SingletonScope())
            b.bind(Encoder).to(AvroEncoder).when_injected_into(AvroProducer).in_scope(
                SingletonScope()
            )
            b.bind(AvroProducer).to(AvroProducer)

    inj = get_injector(C)
    e1 = inj.inject(Encoder)
    e2 = inj.inject(Encoder)
    assert e1 is e2
    assert isinstance(e1, JSONEncoder)

    p1 = inj.inject(AvroProducer)
    p2 = inj.inject(AvroProducer)
    assert isinstance(p1.encoder, AvroEncoder)
    assert p1.encoder is p2.encoder
    assert p1.encoder is not e1


def test_provider_captures_owner_context():
    class C(Config):
        def configure(self):
            self.register(Encoder, JSONEncoder)
            self.register(Encoder, AvroEncoder, when_injected_into=LazyHost)
            self.register(LazyHost, LazyHost)

    inj = get_injector(C)
    host = inj.inject(LazyHost)
    assert isinstance(host.get_encoder(), AvroEncoder)
    assert isinstance(inj.inject(Encoder), JSONEncoder)


def test_install_merges_contextual_bindings():
    class Base(Config):
        def configure(self):
            self.register(Encoder, JSONEncoder)

    class Overlay(Config):
        def configure(self):
            self.register(Encoder, AvroEncoder, when_injected_into=AvroProducer)
            self.register(AvroProducer, AvroProducer)

    class App(Config):
        def configure(self):
            self.install(Base)
            self.install(Overlay)

    inj = get_injector(App)
    assert isinstance(inj.inject(Encoder), JSONEncoder)
    assert isinstance(inj.inject(AvroProducer).encoder, AvroEncoder)


def test_bind_key_rejects_when_injected_into():
    class C(Config):
        def configure(self):
            self.get_binder().bind_key(Key(Encoder, Named("x"))).when_injected_into(AvroProducer)

    with pytest.raises(TypeError, match="type bindings only"):
        C()


def test_parent_injector_contextual():
    class ParentConfig(Config):
        def configure(self):
            self.register(Encoder, JSONEncoder)
            self.register(Encoder, AvroEncoder, when_injected_into=AvroProducer)

    class ChildConfig(Config):
        def configure(self):
            self.register(AvroProducer, AvroProducer)

    root = get_injector(ParentConfig)
    child = root.create_child(ChildConfig)
    assert isinstance(child.inject(AvroProducer).encoder, AvroEncoder)
    assert isinstance(child.inject(Encoder), JSONEncoder)
    assert isinstance(child.inject(Encoder, from_=AvroProducer), AvroEncoder)


def test_register_provider_contextual():
    class AvroProvider:
        def get(self):
            return AvroEncoder()

    class C(Config):
        def configure(self):
            self.register(Encoder, JSONEncoder)
            self.register_provider(Encoder, AvroProvider(), when_injected_into=AvroProducer)
            self.register(AvroProducer, AvroProducer)

    inj = get_injector(C)
    assert isinstance(inj.inject(AvroProducer).encoder, AvroEncoder)
