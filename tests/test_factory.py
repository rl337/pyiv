"""Tests for Factory pattern support."""

from typing import Protocol

import pytest

from pyiv.factory import BaseFactory, Factory, SimpleFactory


class User:
    """Example user class."""

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email


class Database:
    """Example database class."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string


class TestSimpleFactory:
    """Test SimpleFactory implementation."""

    def test_create_from_function(self):
        """Test creating factory from a function."""

        def create_user(name: str, email: str) -> User:
            return User(name=name, email=email)

        factory = SimpleFactory(create_user)
        user = factory.create("Alice", "alice@example.com")

        assert isinstance(user, User)
        assert user.name == "Alice"
        assert user.email == "alice@example.com"

    def test_create_from_class(self):
        """Test creating factory from a class constructor."""
        factory = SimpleFactory(Database)
        db = factory.create("postgresql://localhost/db")

        assert isinstance(db, Database)
        assert db.connection_string == "postgresql://localhost/db"

    def test_create_with_kwargs(self):
        """Test creating factory with keyword arguments."""
        factory = SimpleFactory(User)
        user = factory.create(name="Bob", email="bob@example.com")

        assert isinstance(user, User)
        assert user.name == "Bob"
        assert user.email == "bob@example.com"


class TestBaseFactory:
    """Test BaseFactory abstract base class."""

    def test_base_factory_is_abstract(self):
        """Test that BaseFactory cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseFactory()

    def test_concrete_factory_implementation(self):
        """Test implementing a concrete factory."""

        class UserFactory(BaseFactory[User]):
            def __init__(self, default_email_domain: str):
                self.default_domain = default_email_domain

            def create(self, name: str, email: str = None) -> User:
                if email is None:
                    email = f"{name.lower()}@{self.default_domain}"
                return User(name=name, email=email)

        factory = UserFactory("example.com")
        user = factory.create("Charlie")

        assert isinstance(user, User)
        assert user.name == "Charlie"
        assert user.email == "charlie@example.com"

        # Test with explicit email
        user2 = factory.create("David", "david@custom.com")
        assert user2.email == "david@custom.com"


class TestFactoryProtocol:
    """Test Factory Protocol."""

    def test_simple_factory_implements_protocol(self):
        """Test that SimpleFactory implements Factory protocol."""
        factory = SimpleFactory(User)

        # Should be able to use it as Factory[User]
        def use_factory(f: Factory[User]) -> User:
            return f.create("Test", "test@example.com")

        user = use_factory(factory)
        assert isinstance(user, User)

    def test_base_factory_implements_protocol(self):
        """Test that BaseFactory implements Factory protocol."""

        class UserFactory(BaseFactory[User]):
            def create(self, name: str, email: str) -> User:
                return User(name=name, email=email)

        factory = UserFactory()

        # Should be able to use it as Factory[User]
        def use_factory(f: Factory[User]) -> User:
            return f.create("Test", "test@example.com")

        user = use_factory(factory)
        assert isinstance(user, User)

