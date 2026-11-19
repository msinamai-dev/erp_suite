"""Which company is the current request working for? Every company-owned query is filtered by this."""
from contextlib import contextmanager
from contextvars import ContextVar

_company_id = ContextVar("erp_company_id", default=None)
_currency_code = ContextVar("erp_currency_code", default=None)

NO_ACCESS = -1  # matches no company: used to fail closed for signed-in users who belong to none


def current_company_id():
    """The company id queries are limited to, or None for unrestricted (superusers, shell, commands)."""
    return _company_id.get()


def set_company_id(value):
    return _company_id.set(value)


def reset_company_id(token):
    _company_id.reset(token)


@contextmanager
def company_context(company_id):
    """Run a block (seed script, shell, command) as if signed in to that company."""
    token = _company_id.set(company_id)
    try:
        yield
    finally:
        _company_id.reset(token)


def current_currency_code():
    return _currency_code.get()


def set_currency_code(value):
    return _currency_code.set(value)


def reset_currency_code(token):
    _currency_code.reset(token)
