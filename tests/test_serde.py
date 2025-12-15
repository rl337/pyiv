"""Tests for SerDe interface and dependency injection integration."""

import json
from datetime import datetime
from typing import Any

import pytest

from pyiv import Config, get_injector
from pyiv.serde import GRPCJSONSerDe, JSONSerDe, SerDe, StandardJSONSerDe


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

    def test_serde_encoding_type(self):
        """Test that SerDe implementations have encoding_type property."""
        serde = StandardJSONSerDe()
        assert serde.encoding_type == "json"

    def test_serde_serialize_deserialize(self):
        """Test basic serialize/deserialize functionality."""
        serde = StandardJSONSerDe()
        data = {"key": "value", "number": 42}
        serialized = serde.serialize(data)
        assert isinstance(serialized, str)
        deserialized = serde.deserialize(serialized)
        assert deserialized == data

    def test_serde_datetime_serialization(self):
        """Test datetime serialization."""
        serde = StandardJSONSerDe()
        dt = datetime(2024, 1, 1, 12, 0, 0)
        data = {"timestamp": dt}
        serialized = serde.serialize(data)
        assert "2024-01-01T12:00:00" in serialized
        deserialized = serde.deserialize(serialized)
        assert isinstance(deserialized["timestamp"], str)

    def test_serde_bytes_input(self):
        """Test deserializing from bytes."""
        serde = StandardJSONSerDe()
        data = {"key": "value"}
        serialized = serde.serialize(data)
        bytes_data = serialized.encode("utf-8")
        deserialized = serde.deserialize(bytes_data)
        assert deserialized == data


class TestJSONSerDeImplementations:
    """Tests for JSON SerDe implementations."""

    def test_standard_json_serde(self):
        """Test StandardJSONSerDe."""
        serde = StandardJSONSerDe()
        data = {"key": "value"}
        serialized = serde.serialize(data)
        assert serialized == '{"key":"value"}'
        deserialized = serde.deserialize(serialized)
        assert deserialized == data

    def test_grpc_json_serde(self):
        """Test GRPCJSONSerDe."""
        serde = GRPCJSONSerDe()
        data = {"key": "value"}
        serialized = serde.serialize(data)
        assert serialized == '{"key":"value"}'
        deserialized = serde.deserialize(serialized)
        assert deserialized == data

    def test_custom_json_serde(self):
        """Test custom JSON SerDe with different date formatting."""
        serde = CustomJSONSerDe()
        dt = datetime(2024, 1, 1, 12, 0, 0)
        data = {"timestamp": dt}
        serialized = serde.serialize(data)
        assert "2024-01-01 12:00:00" in serialized
        # Standard JSON SerDe would use ISO format
        standard_serde = StandardJSONSerDe()
        standard_serialized = standard_serde.serialize(data)
        assert serialized != standard_serialized


class TestSerDeConfigRegistration:
    """Tests for SerDe registration in Config."""

    def test_register_serde_by_type(self):
        """Test registering SerDe by encoding type."""

        class MyConfig(Config):
            def configure(self):
                self.register_serde("json", StandardJSONSerDe)

        config = MyConfig()
        assert config.has_serde_registration("json")
        assert config.get_serde_registration("json") == StandardJSONSerDe

    def test_register_serde_by_name(self):
        """Test registering SerDe by name."""

        class MyConfig(Config):
            def configure(self):
                self.register_serde_by_name("json-grpc", GRPCJSONSerDe, "json")

        config = MyConfig()
        assert config.has_serde_registration_by_name("json-grpc")
        registration = config.get_serde_registration_by_name("json-grpc")
        assert registration is not None
        serde_class, encoding_type = registration
        assert serde_class == GRPCJSONSerDe
        assert encoding_type == "json"

    def test_register_multiple_serde_instances(self):
        """Test registering multiple SerDe instances of the same type."""

        class MyConfig(Config):
            def configure(self):
                self.register_serde_by_name("json-input", CustomJSONSerDe, "json")
                self.register_serde_by_name("json-output", StandardJSONSerDe, "json")

        config = MyConfig()
        assert config.has_serde_registration_by_name("json-input")
        assert config.has_serde_registration_by_name("json-output")

    def test_register_serde_instance(self):
        """Test registering a pre-created SerDe instance."""

        class MyConfig(Config):
            def configure(self):
                instance = StandardJSONSerDe()
                self.register_serde_instance("json-precreated", instance)

        config = MyConfig()
        instance = config.get_serde_instance("json-precreated")
        assert instance is not None
        assert isinstance(instance, StandardJSONSerDe)

    def test_register_serde_validation(self):
        """Test that SerDe registration validates inputs."""

        class MyConfig(Config):
            def configure(self):
                pass

        config = MyConfig()

        # Empty encoding_type
        with pytest.raises(ValueError, match="encoding_type must be a non-empty string"):
            config.register_serde("", StandardJSONSerDe)

        # Invalid serde_class
        with pytest.raises(TypeError, match="serde_class must be a subclass of SerDe"):
            config.register_serde("json", str)  # type: ignore[arg-type]

        # Empty name
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            config.register_serde_by_name("", StandardJSONSerDe, "json")


class TestSerDeInjection:
    """Tests for SerDe injection via Injector."""

    def test_inject_serde_by_type(self):
        """Test injecting SerDe by encoding type."""

        class MyConfig(Config):
            def configure(self):
                self.register_serde("json", StandardJSONSerDe)

        injector = get_injector(MyConfig)
        serde = injector.inject_serde("json")
        assert isinstance(serde, StandardJSONSerDe)

    def test_inject_serde_by_name(self):
        """Test injecting SerDe by name."""

        class MyConfig(Config):
            def configure(self):
                self.register_serde_by_name("json-grpc", GRPCJSONSerDe, "json")

        injector = get_injector(MyConfig)
        serde = injector.inject_serde_by_name("json-grpc")
        assert isinstance(serde, GRPCJSONSerDe)

    def test_inject_multiple_serde_instances(self):
        """Test injecting multiple SerDe instances of the same type."""

        class MyConfig(Config):
            def configure(self):
                self.register_serde_by_name("json-input", CustomJSONSerDe, "json")
                self.register_serde_by_name("json-output", StandardJSONSerDe, "json")

        injector = get_injector(MyConfig)
        input_serde = injector.inject_serde_by_name("json-input")
        output_serde = injector.inject_serde_by_name("json-output")

        assert isinstance(input_serde, CustomJSONSerDe)
        assert isinstance(output_serde, StandardJSONSerDe)

        # Test that they have different behaviors
        dt = datetime(2024, 1, 1, 12, 0, 0)
        data = {"timestamp": dt}
        input_serialized = input_serde.serialize(data)
        output_serialized = output_serde.serialize(data)
        assert input_serialized != output_serialized

    def test_inject_serde_singleton(self):
        """Test that SerDe instances respect singleton configuration."""

        class MyConfig(Config):
            def configure(self):
                self.register_serde("json", StandardJSONSerDe)

        injector = get_injector(MyConfig)
        serde1 = injector.inject_serde("json")
        serde2 = injector.inject_serde("json")
        # Should be the same instance (singleton)
        assert serde1 is serde2

    def test_inject_serde_precreated_instance(self):
        """Test injecting a pre-created SerDe instance."""

        class MyConfig(Config):
            def configure(self):
                instance = StandardJSONSerDe()
                self.register_serde_instance("json-precreated", instance)

        injector = get_injector(MyConfig)
        serde = injector.inject_serde_by_name("json-precreated")
        assert isinstance(serde, StandardJSONSerDe)
        # Should be the exact same instance
        serde2 = injector.inject_serde_by_name("json-precreated")
        assert serde is serde2

    def test_inject_serde_not_found(self):
        """Test that injection fails for unregistered SerDe."""

        class MyConfig(Config):
            def configure(self):
                pass

        injector = get_injector(MyConfig)

        with pytest.raises(ValueError, match="No SerDe registered for encoding type"):
            injector.inject_serde("json")

        with pytest.raises(ValueError, match="No SerDe registered with name"):
            injector.inject_serde_by_name("json-grpc")


class TestSerDeIntegration:
    """Integration tests for SerDe with dependency injection."""

    def test_serde_in_class_constructor(self):
        """Test injecting SerDe into a class constructor."""

        class DataProcessor:
            """A class that uses SerDe for data processing."""

            def __init__(self, json_serde: JSONSerDe):
                self.serde = json_serde

            def process(self, data: dict) -> str:
                return self.serde.serialize(data)

        class MyConfig(Config):
            def configure(self):
                self.register_serde("json", StandardJSONSerDe)

        injector = get_injector(MyConfig)
        # Manually inject SerDe and create processor
        serde = injector.inject_serde("json")
        processor = DataProcessor(serde)
        result = processor.process({"key": "value"})
        assert result == '{"key":"value"}'

    def test_multiple_serde_types(self):
        """Test registering and injecting multiple encoding types."""

        class MessagePackSerDe(SerDe):
            """Mock MessagePack SerDe for testing."""

            @property
            def encoding_type(self) -> str:
                return "msgpack"

            def serialize(self, obj: Any) -> bytes:
                # Mock implementation
                return json.dumps(obj).encode("utf-8")

            def deserialize(self, data: str | bytes, target_type: type | None = None):
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                return json.loads(data)

        class MyConfig(Config):
            def configure(self):
                self.register_serde("json", StandardJSONSerDe)
                self.register_serde("msgpack", MessagePackSerDe)

        injector = get_injector(MyConfig)
        json_serde = injector.inject_serde("json")
        msgpack_serde = injector.inject_serde("msgpack")

        assert isinstance(json_serde, StandardJSONSerDe)
        assert isinstance(msgpack_serde, MessagePackSerDe)
        assert json_serde.encoding_type == "json"
        assert msgpack_serde.encoding_type == "msgpack"

