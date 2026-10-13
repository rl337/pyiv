"""Tests for plugin catalog introspection APIs."""

from __future__ import annotations

from typing import Dict

import pytest

from pyiv import Config, get_injector
from pyiv.key import Key, Named


class Recipe:
    name: str = "recipe"


class HarnessRun(Recipe):
    name = "harness_run"

    def __init__(self) -> None:
        self.name = "harness_run"


class VerifyRepair(Recipe):
    name = "verify_repair"

    def __init__(self) -> None:
        self.name = "verify_repair"


class ExplodingRecipe(Recipe):
    name = "boom"

    def __init__(self) -> None:
        raise RuntimeError("must not construct for catalog_keys")


class RecipeHost:
    def __init__(self, recipes: Dict[str, Recipe]):
        self.recipes = recipes


def test_catalog_keys_lists_map_multibind_without_constructing():
    class CatalogConfig(Config):
        def configure(self):
            mb = self.map_multibinder(Recipe)
            mb.add("boom", ExplodingRecipe)
            mb.add("harness_run", HarnessRun)

    injector = get_injector(CatalogConfig)
    assert injector.catalog_keys(Recipe) == ["boom", "harness_run"]


def test_catalog_keys_empty_when_unbound():
    class EmptyConfig(Config):
        def configure(self):
            pass

    assert get_injector(EmptyConfig).catalog_keys(Recipe) == []


def test_catalog_keys_includes_instance_only_keys():
    class InstanceConfig(Config):
        def configure(self):
            mb = self.map_multibinder(Recipe)
            mb.add("harness_run", HarnessRun)
            mb.add_instance("prebuilt", VerifyRepair())

    keys = get_injector(InstanceConfig).catalog_keys(Recipe)
    assert keys == ["harness_run", "prebuilt"]


def test_catalog_keys_after_install_merges():
    class LibraryConfig(Config):
        def configure(self):
            self.map_multibinder(Recipe).add("harness_run", HarnessRun)

    class HostConfig(Config):
        def configure(self):
            self.install(LibraryConfig)
            self.map_multibinder(Recipe).add("verify_repair", VerifyRepair)

    assert get_injector(HostConfig).catalog_keys(Recipe) == [
        "harness_run",
        "verify_repair",
    ]


def test_catalog_keys_match_injected_map():
    class CatalogConfig(Config):
        def configure(self):
            mb = self.map_multibinder(Recipe)
            mb.add("verify_repair", VerifyRepair)
            mb.add("harness_run", HarnessRun)

    injector = get_injector(CatalogConfig)
    keys = injector.catalog_keys(Recipe)
    host = injector.inject(RecipeHost)
    assert set(host.recipes) == set(keys)


def test_named_keys_lists_named_qualifiers():
    class Encoder:
        pass

    class JsonEncoder(Encoder):
        pass

    class XmlEncoder(Encoder):
        pass

    class NamedConfig(Config):
        def configure(self):
            self.register_key(Key(Encoder, Named("xml")), XmlEncoder)
            self.register_key(Key(Encoder, Named("json")), JsonEncoder)

    named = get_injector(NamedConfig).named_keys(Encoder)
    assert [sorted(n.tags) for n in named] == [["json"], ["xml"]]


def test_named_keys_empty_when_unbound():
    class Encoder:
        pass

    class EmptyConfig(Config):
        def configure(self):
            pass

    assert get_injector(EmptyConfig).named_keys(Encoder) == []


def test_contribute_map_replace_default():
    class Lib(Config):
        def configure(self):
            self.contribute_map(Recipe, "harness_run", HarnessRun)

    class Host(Config):
        def configure(self):
            self.install(Lib)
            self.contribute_map(Recipe, "harness_run", VerifyRepair)

    binding = Host().get_map_multibinding(Recipe)
    assert binding is not None
    impls, _instances = binding
    assert impls["harness_run"] is VerifyRepair


def test_contribute_map_error_on_conflict():
    class Lib(Config):
        def configure(self):
            self.contribute_map(Recipe, "harness_run", HarnessRun)

    class Host(Config):
        def configure(self):
            self.install(Lib)
            self.contribute_map(Recipe, "harness_run", VerifyRepair, on_conflict="error")

    with pytest.raises(ValueError, match="harness_run"):
        Host()


def test_contribute_map_keep_on_conflict():
    class Lib(Config):
        def configure(self):
            self.contribute_map(Recipe, "harness_run", HarnessRun)

    class Host(Config):
        def configure(self):
            self.install(Lib)
            self.contribute_map(Recipe, "harness_run", VerifyRepair, on_conflict="keep")

    binding = Host().get_map_multibinding(Recipe)
    assert binding is not None
    impls, _instances = binding
    assert impls["harness_run"] is HarnessRun


def test_contribute_map_entries():
    class ToolsConfig(Config):
        def configure(self):
            self.contribute_map_entries(
                Recipe,
                {"harness_run": HarnessRun, "verify_repair": VerifyRepair},
                on_conflict="error",
            )

    assert get_injector(ToolsConfig).catalog_keys(Recipe) == [
        "harness_run",
        "verify_repair",
    ]
