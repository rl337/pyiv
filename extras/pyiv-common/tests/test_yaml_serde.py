"""Tests for pyiv-common YAMLSerDe."""

from pyiv import ChainType, Config, get_injector
from pyiv_common.serde import YAMLSerDe


class TestYAMLSerDe:
    def test_handler_type(self):
        serde = YAMLSerDe()
        assert serde.handler_type == "yaml"
        assert serde.chain_type == ChainType.ENCODING

    def test_round_trip_dict(self):
        serde = YAMLSerDe()
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        serialized = serde.serialize(data)
        assert isinstance(serialized, str)
        assert "key" in serialized
        assert serde.deserialize(serialized) == data

    def test_deserialize_bytes(self):
        serde = YAMLSerDe()
        data = {"hello": "world"}
        raw = serde.serialize(data).encode("utf-8")
        assert serde.deserialize(raw) == data

    def test_inject_chain_handler(self):
        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.ENCODING, "yaml", YAMLSerDe)

        injector = get_injector(MyConfig)
        serde = injector.inject_chain_handler(ChainType.ENCODING, "yaml")
        assert isinstance(serde, YAMLSerDe)
        assert serde.deserialize(serde.serialize({"x": True})) == {"x": True}
