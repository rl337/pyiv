"""Tests for Config.multibinder() wiring into the injector."""

from typing import List, Set

from pyiv import Config, get_injector


class EventHandler:
    pass


class EmailHandler(EventHandler):
    pass


class SMSHandler(EventHandler):
    pass


class HandlerHost:
    def __init__(self, handlers: Set[EventHandler]):
        self.handlers = handlers


class Validator:
    pass


class EmailValidator(Validator):
    pass


class PhoneValidator(Validator):
    pass


class ValidatorHost:
    def __init__(self, validators: List[Validator]):
        self.validators = validators


def test_set_multibinder_add_is_injected():
    class MyConfig(Config):
        def configure(self):
            multibinder = self.multibinder(EventHandler, as_set=True)
            multibinder.add(EmailHandler)
            multibinder.add(SMSHandler)

    handlers = get_injector(MyConfig).inject(HandlerHost).handlers
    assert {type(h) for h in handlers} == {EmailHandler, SMSHandler}


def test_list_multibinder_preserves_order():
    class MyConfig(Config):
        def configure(self):
            multibinder = self.multibinder(Validator, as_set=False)
            multibinder.add(EmailValidator)
            multibinder.add(PhoneValidator)

    validators = get_injector(MyConfig).inject(ValidatorHost).validators
    assert [type(v) for v in validators] == [EmailValidator, PhoneValidator]
