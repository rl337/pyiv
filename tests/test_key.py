"""Tests for qualified Key bindings, Named tag sets, and Matched resolution."""

from abc import ABC

import pytest

from pyiv import Config, CreationError, get_injector
from pyiv.key import Key, Matched, Named


class Database:
    def __init__(self, name: str = "default"):
        self.name = name


class PostgreSQL(Database):
    def __init__(self):
        super().__init__("postgresql")


class MySQL(Database):
    def __init__(self):
        super().__init__("mysql")


class Encoder:
    def __init__(self, kind: str = "base"):
        self.kind = kind


class JSONEncoder(Encoder):
    def __init__(self):
        super().__init__("json")


class PrettyJSONEncoder(Encoder):
    def __init__(self):
        super().__init__("pretty")


class AvroEncoder(Encoder):
    def __init__(self):
        super().__init__("avro")


def test_key_accepts_user_types():
    """Key(SomeClass) must not confuse the class with the builtin type()."""
    key = Key(Database, Named("primary"))
    assert key.type is Database
    assert key.qualifier == Named("primary")


def test_named_scalar_equals_list():
    assert Named("json") == Named(["json"])
    assert Named("json") == Named(("json",))
    assert hash(Named("json")) == hash(Named(["json"]))
    assert Named(["a", "b"]) == Named(("b", "a"))
    assert Named("x", default=True) == Named("x", default=False)


def test_named_rejects_empty_and_bad_types():
    with pytest.raises(ValueError):
        Named("")
    with pytest.raises(ValueError):
        Named([])
    with pytest.raises(TypeError):
        Named([1])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        Named({"a"})  # type: ignore[arg-type]


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


def test_register_key_rejects_matched():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Encoder, Matched(required=["json"])), JSONEncoder)

    with pytest.raises(TypeError, match="inject-only"):
        MyConfig()


def test_duplicate_named_tag_set_raises():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("json")), JSONEncoder)
            self.register_key(Key(Encoder, Named(["json"])), PrettyJSONEncoder)

    with pytest.raises(ValueError, match="Duplicate Named"):
        MyConfig()


def test_second_default_raises():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("json", default=True)), JSONEncoder)
            self.register_key(Key(Encoder, Named("avro", default=True)), AvroEncoder)

    with pytest.raises(ValueError, match="default=True"):
        MyConfig()


def test_matched_prefer_and_bare_default():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("json")), JSONEncoder)
            self.register_key(
                Key(Encoder, Named(["json", "pretty"], default=True)),
                PrettyJSONEncoder,
            )

    inj = get_injector(MyConfig)
    assert inj.inject(Key(Encoder, Named("json"))).kind == "json"
    assert inj.inject(Key(Encoder, Matched(required=["json"], prefer=["pretty"]))).kind == "pretty"
    assert inj.inject(Encoder).kind == "pretty"


def test_bare_inject_sole_named_without_default():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("json")), JSONEncoder)

    assert get_injector(MyConfig).inject(Encoder).kind == "json"


def test_bare_inject_ambiguous_without_default():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("json")), JSONEncoder)
            self.register_key(Key(Encoder, Named("avro")), AvroEncoder)

    with pytest.raises(CreationError, match="Ambiguous") as exc_info:
        get_injector(MyConfig).inject(Encoder)
    assert exc_info.value.ambiguous is True


def test_matched_ambiguous_without_default():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("json")), JSONEncoder)
            self.register_key(Key(Encoder, Named(["json", "pretty"])), PrettyJSONEncoder)

    with pytest.raises(CreationError, match="Ambiguous Matched") as exc_info:
        get_injector(MyConfig).inject(Key(Encoder, Matched(required=["json"], prefer=[])))
    assert exc_info.value.ambiguous is True


def test_unqualified_wins_over_named_for_bare_inject():
    class MyConfig(Config):
        def configure(self):
            self.register(Encoder, AvroEncoder)
            self.register_key(
                Key(Encoder, Named("json", default=True)),
                JSONEncoder,
            )

    assert isinstance(get_injector(MyConfig).inject(Encoder), AvroEncoder)


def test_optional_ambiguity_raises():
    from abc import abstractmethod
    from typing import Optional

    class Codec(ABC):
        @abstractmethod
        def name(self) -> str:
            raise NotImplementedError

    class JsonCodec(Codec):
        def name(self) -> str:
            return "json"

    class AvroCodec(Codec):
        def name(self) -> str:
            return "avro"

    class Host:
        def __init__(self, codec: Optional[Codec] = None):
            self.codec = codec

    class MissingConfig(Config):
        def configure(self):
            pass

    assert get_injector(MissingConfig).inject(Host).codec is None

    class AmbiguousCodecConfig(Config):
        def configure(self):
            self.register_key(Key(Codec, Named("json")), JsonCodec)
            self.register_key(Key(Codec, Named("avro")), AvroCodec)

    with pytest.raises(CreationError, match="Ambiguous"):
        get_injector(AmbiguousCodecConfig).inject(Host)


def test_install_replace_same_named_tags():
    class Base(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("json")), JSONEncoder)

    class Overlay(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("json")), PrettyJSONEncoder)

    class Combined(Config):
        def configure(self):
            self.install(Base)
            self.install(Overlay)

    assert get_injector(Combined).inject(Key(Encoder, Named("json"))).kind == "pretty"


def test_binder_bind_key_with_tags():
    class MyConfig(Config):
        def configure(self):
            binder = self.get_binder()
            binder.bind_key(Key(Encoder, Named(["json", "pretty"], default=True))).to(
                PrettyJSONEncoder
            )

    assert get_injector(MyConfig).inject(Encoder).kind == "pretty"


# --- Regression: pre-tag-set Key/Named behaviors must hold ---


def test_missing_named_key_raises_non_ambiguous():
    class MyConfig(Config):
        def configure(self):
            self.register_key(Key(Database, Named("primary")), PostgreSQL)

    with pytest.raises(CreationError, match="No binding found for key") as exc_info:
        get_injector(MyConfig).inject(Key(Database, Named("missing")))
    assert exc_info.value.ambiguous is False


def test_wrong_named_does_not_soft_match_or_fall_through():
    class MyConfig(Config):
        def configure(self):
            self.register(Encoder, AvroEncoder)
            self.register_key(Key(Encoder, Named("primary")), JSONEncoder)

    inj = get_injector(MyConfig)
    with pytest.raises(CreationError, match="No binding found for key"):
        inj.inject(Key(Encoder, Named("Primary")))
    with pytest.raises(CreationError, match="No binding found for key"):
        inj.inject(Key(Encoder, Named("replica")))
    # Unqualified binding is unchanged and still separate from Named lookups
    assert isinstance(inj.inject(Encoder), AvroEncoder)


def test_unqualified_and_named_stores_remain_separate():
    class MyConfig(Config):
        def configure(self):
            self.register(Encoder, AvroEncoder)
            self.register_key(Key(Encoder, Named("json")), JSONEncoder)

    inj = get_injector(MyConfig)
    assert isinstance(inj.inject(Encoder), AvroEncoder)
    assert isinstance(inj.inject(Key(Encoder, Named("json"))), JSONEncoder)


def test_named_scalar_name_and_repr_back_compat():
    named = Named("primary")
    assert named.name == "primary"
    assert named.tags == frozenset({"primary"})
    assert repr(named) == "Named('primary')"
