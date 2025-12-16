"""Tests for SerDe interface and dependency injection integration."""

import json
from datetime import datetime
from typing import Any

import pytest

from pyiv import ChainType, Config, get_injector
from pyiv.serde import (
    Base64SerDe,
    JSONSerDe,
    NoOpSerDe,
    PickleSerDe,
    SerDe,
    UUEncodeSerDe,
    XMLSerDe,
    YAMLSerDe,
)


class CustomJSONSerDe(JSONSerDe):
    """Custom JSON SerDe with different date formatting."""

    def _default_serializer(self, obj):
        """Custom date serializer."""
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super()._default_serializer(obj)


class TestSerDeInterface:
    """Tests for the SerDe base interface."""

    def test_serde_is_abstract(self):
        """Test that SerDe cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SerDe()  # type: ignore[abstract]

    def test_serde_handler_type(self):
        """Test that SerDe implementations have handler_type property."""
        serde = JSONSerDe()
        assert serde.handler_type == "json"
        assert serde.chain_type == ChainType.ENCODING

    def test_serde_serialize_deserialize(self):
        """Test basic serialize/deserialize functionality."""
        serde = JSONSerDe()
        data = {"key": "value", "number": 42}
        serialized = serde.serialize(data)
        assert isinstance(serialized, str)
        deserialized = serde.deserialize(serialized)
        assert deserialized == data

    def test_serde_datetime_serialization(self):
        """Test datetime serialization."""
        serde = JSONSerDe()
        dt = datetime(2024, 1, 1, 12, 0, 0)
        data = {"timestamp": dt}
        # JSON uses default serializer which converts datetime to ISO format
        serialized = serde.serialize(data)
        assert isinstance(serialized, str)
        assert "2024-01-01T12:00:00" in serialized
        deserialized = serde.deserialize(serialized)
        assert isinstance(deserialized, dict)
        assert "timestamp" in deserialized

    def test_serde_bytes_input(self):
        """Test deserializing from bytes."""
        serde = JSONSerDe()
        data = {"key": "value"}
        serialized = serde.serialize(data)
        bytes_data = serialized.encode("utf-8")
        deserialized = serde.deserialize(bytes_data)
        assert deserialized == data

    def test_serde_chain_handler_interface(self):
        """Test that SerDe implements ChainHandler interface."""
        serde = JSONSerDe()
        # Test handle() method
        data = {"key": "value"}
        result = serde.handle(("serialize", data))
        assert isinstance(result, str)
        assert "key" in result


class TestSerDeImplementations:
    """Tests for SerDe implementations."""

    def test_json_serde(self):
        """Test JSONSerDe."""
        serde = JSONSerDe()
        data = {"key": "value"}
        serialized = serde.serialize(data)
        # JSON may include spaces, so check content rather than exact format
        assert '"key"' in serialized and '"value"' in serialized
        deserialized = serde.deserialize(serialized)
        assert deserialized == data

    def test_noop_serde(self):
        """Test NoOpSerDe."""
        serde = NoOpSerDe()
        data = "test data"
        serialized = serde.serialize(data)
        assert serialized == data
        deserialized = serde.deserialize(serialized)
        assert deserialized == data

    def test_pickle_serde(self):
        """Test PickleSerDe."""
        serde = PickleSerDe()
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        serialized = serde.serialize(data)
        assert isinstance(serialized, bytes)
        deserialized = serde.deserialize(serialized)
        assert deserialized == data

    def test_base64_serde(self):
        """Test Base64SerDe."""
        serde = Base64SerDe()
        data = b"test data"
        serialized = serde.serialize(data)
        assert isinstance(serialized, str)
        deserialized = serde.deserialize(serialized)
        assert deserialized == data

    def test_xml_serde(self):
        """Test XMLSerDe."""
        serde = XMLSerDe()
        data = {"key": "value", "number": 42}
        serialized = serde.serialize(data)
        assert isinstance(serialized, str)
        assert "<root>" in serialized
        deserialized = serde.deserialize(serialized)
        assert isinstance(deserialized, dict)

    def test_custom_json_serde(self):
        """Test custom JSON SerDe with different date formatting."""
        serde = CustomJSONSerDe()
        dt = datetime(2024, 1, 1, 12, 0, 0)
        data = {"timestamp": dt}
        serialized = serde.serialize(data)
        assert "2024-01-01 12:00:00" in serialized
        # Standard JSON SerDe would use different format
        standard_serde = JSONSerDe()
        standard_serialized = standard_serde.serialize(data)
        assert serialized != standard_serialized


class TestChainHandlerConfigRegistration:
    """Tests for chain handler registration in Config."""

    def test_register_chain_handler_by_type(self):
        """Test registering chain handler by handler type."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.ENCODING, "json", JSONSerDe)

        config = MyConfig()
        assert config.has_chain_handler_registration(ChainType.ENCODING, "json")
        assert config.get_chain_handler_registration(ChainType.ENCODING, "json") == JSONSerDe

    def test_register_chain_handler_by_name(self):
        """Test registering chain handler by name."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler_by_name(ChainType.ENCODING, "json-input", JSONSerDe, "json")

        config = MyConfig()
        assert config.has_chain_handler_registration_by_name(ChainType.ENCODING, "json-input")
        registration = config.get_chain_handler_registration_by_name(ChainType.ENCODING, "json-input")
        assert registration is not None
        handler_class, handler_type = registration
        assert handler_class == JSONSerDe
        assert handler_type == "json"

    def test_register_multiple_chain_handlers(self):
        """Test registering multiple chain handler instances of the same type."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler_by_name(ChainType.ENCODING, "json-input", CustomJSONSerDe, "json")
                self.register_chain_handler_by_name(ChainType.ENCODING, "json-output", JSONSerDe, "json")

        config = MyConfig()
        assert config.has_chain_handler_registration_by_name(ChainType.ENCODING, "json-input")
        assert config.has_chain_handler_registration_by_name(ChainType.ENCODING, "json-output")

    def test_register_chain_handler_instance(self):
        """Test registering a pre-created chain handler instance."""

        class MyConfig(Config):
            def configure(self):
                instance = JSONSerDe()
                self.register_chain_handler_instance(ChainType.ENCODING, "json-precreated", instance)

        config = MyConfig()
        instance = config.get_chain_handler_instance(ChainType.ENCODING, "json-precreated")
        assert instance is not None
        assert isinstance(instance, JSONSerDe)

    def test_register_chain_handler_validation(self):
        """Test that chain handler registration validates inputs."""

        class MyConfig(Config):
            def configure(self):
                pass

        config = MyConfig()

        # Empty handler_type
        with pytest.raises(ValueError, match="handler_type must be a non-empty string"):
            config.register_chain_handler(ChainType.ENCODING, "", JSONSerDe)

        # Invalid handler_class
        with pytest.raises(TypeError, match="handler_class must be a subclass of ChainHandler"):
            config.register_chain_handler(ChainType.ENCODING, "json", str)  # type: ignore[arg-type]

        # Empty name
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            config.register_chain_handler_by_name(ChainType.ENCODING, "", JSONSerDe, "json")


class TestChainHandlerInjection:
    """Tests for chain handler injection via Injector."""

    def test_inject_chain_handler_by_type(self):
        """Test injecting chain handler by handler type."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.ENCODING, "json", JSONSerDe)

        injector = get_injector(MyConfig)
        serde = injector.inject_chain_handler(ChainType.ENCODING, "json")
        assert isinstance(serde, JSONSerDe)

    def test_inject_chain_handler_by_name(self):
        """Test injecting chain handler by name."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler_by_name(ChainType.ENCODING, "json-input", JSONSerDe, "json")

        injector = get_injector(MyConfig)
        serde = injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-input")
        assert isinstance(serde, JSONSerDe)

    def test_inject_multiple_chain_handlers(self):
        """Test injecting multiple chain handler instances of the same type."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler_by_name(ChainType.ENCODING, "json-input", CustomJSONSerDe, "json")
                self.register_chain_handler_by_name(ChainType.ENCODING, "json-output", JSONSerDe, "json")

        injector = get_injector(MyConfig)
        input_serde = injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-input")
        output_serde = injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-output")

        assert isinstance(input_serde, CustomJSONSerDe)
        assert isinstance(output_serde, JSONSerDe)

        # Test that they have different behaviors
        dt = datetime(2024, 1, 1, 12, 0, 0)
        data = {"timestamp": dt}
        input_serialized = input_serde.serialize(data)
        output_serialized = output_serde.serialize(data)
        assert input_serialized != output_serialized

    def test_inject_chain_handler_singleton(self):
        """Test that chain handler instances respect singleton configuration."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.ENCODING, "json", JSONSerDe)

        injector = get_injector(MyConfig)
        serde1 = injector.inject_chain_handler(ChainType.ENCODING, "json")
        serde2 = injector.inject_chain_handler(ChainType.ENCODING, "json")
        # Should be the same instance (singleton)
        assert serde1 is serde2

    def test_inject_chain_handler_precreated_instance(self):
        """Test injecting a pre-created chain handler instance."""

        class MyConfig(Config):
            def configure(self):
                instance = JSONSerDe()
                self.register_chain_handler_instance(ChainType.ENCODING, "json-precreated", instance)

        injector = get_injector(MyConfig)
        serde = injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-precreated")
        assert isinstance(serde, JSONSerDe)
        # Should be the exact same instance
        serde2 = injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-precreated")
        assert serde is serde2

    def test_inject_chain_handler_not_found(self):
        """Test that injection fails for unregistered chain handlers."""

        class MyConfig(Config):
            def configure(self):
                pass

        injector = get_injector(MyConfig)

        with pytest.raises(ValueError, match="No chain handler registered"):
            injector.inject_chain_handler(ChainType.ENCODING, "json")

        with pytest.raises(ValueError, match="No chain handler registered"):
            injector.inject_chain_handler_by_name(ChainType.ENCODING, "json-input")


class TestChainHandlerIntegration:
    """Integration tests for chain handlers with dependency injection."""

    def test_chain_handler_in_class_constructor(self):
        """Test injecting chain handler into a class constructor."""

        class DataProcessor:
            """A class that uses SerDe for data processing."""

            def __init__(self, json_serde: JSONSerDe):
                self.serde = json_serde

            def process(self, data: dict) -> str:
                return self.serde.serialize(data)

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.ENCODING, "json", JSONSerDe)

        injector = get_injector(MyConfig)
        # Manually inject chain handler and create processor
        serde = injector.inject_chain_handler(ChainType.ENCODING, "json")
        processor = DataProcessor(serde)
        result = processor.process({"key": "value"})
        # JSON may include spaces, so check content rather than exact format
        assert '"key"' in result and '"value"' in result

    def test_multiple_encoding_types(self):
        """Test registering and injecting multiple encoding types."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.ENCODING, "json", JSONSerDe)
                self.register_chain_handler(ChainType.ENCODING, "pickle", PickleSerDe)
                self.register_chain_handler(ChainType.ENCODING, "base64", Base64SerDe)

        injector = get_injector(MyConfig)
        json_serde = injector.inject_chain_handler(ChainType.ENCODING, "json")
        pickle_serde = injector.inject_chain_handler(ChainType.ENCODING, "pickle")
        base64_serde = injector.inject_chain_handler(ChainType.ENCODING, "base64")

        assert isinstance(json_serde, JSONSerDe)
        assert isinstance(pickle_serde, PickleSerDe)
        assert isinstance(base64_serde, Base64SerDe)
        assert json_serde.handler_type == "json"
        assert pickle_serde.handler_type == "pickle"
        assert base64_serde.handler_type == "base64"

    def test_default_noop_serde(self):
        """Test that NoOpSerDe can be used as a default."""

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.ENCODING, "default", NoOpSerDe)

        injector = get_injector(MyConfig)
        serde = injector.inject_chain_handler(ChainType.ENCODING, "default")
        assert isinstance(serde, NoOpSerDe)
        # Test pass-through behavior
        data = "test"
        assert serde.serialize(data) == data
        assert serde.deserialize(data) == data
