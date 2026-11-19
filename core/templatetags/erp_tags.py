from datetime import date, datetime
from decimal import Decimal

from django import template
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.utils import timezone
from django.utils.html import format_html

from core.tenancy import current_currency_code

register = template.Library()

OK = {"paid", "active", "completed", "approved", "closed", "available", "received",
      "resolved", "delivered", "occupied", "done", "owned"}
WARN = {"pending", "draft", "open", "planning", "on_leave", "on_hold", "medium",
        "maintenance", "repair", "development", "todo"}
BAD = {"cancelled", "overdue", "rejected", "critical", "terminated", "high",
       "expired", "blocked"}
INFO = {"in_progress", "sent", "ordered", "confirmed", "in_use", "leased_out", "for_sale"}


def tone(value):
    v = str(value)
    if v in OK:
        return "ok"
    if v in WARN:
        return "warn"
    if v in BAD:
        return "bad"
    if v in INFO:
        return "info"
    return "neutral"


@register.simple_tag
def cell(obj, name):
    """Render one table cell: status tags, money, progress bars, booleans, dashes for blanks."""
    try:
        field = obj._meta.get_field(name)
    except FieldDoesNotExist:
        field = None
    value = getattr(obj, name, None)
    if callable(value):
        value = value()
    if field is not None and getattr(field, "choices", None):
        return format_html(
            '<span class="tag tag-{}">{}</span>',
            tone(value), getattr(obj, f"get_{name}_display")(),
        )
    if value is None or value == "":
        return "—"
    if name == "progress":
        return format_html(
            '<div class="meter" title="{0}%"><span style="width:{0}%"></span></div>'
            '<small class="text-muted">{0}%</small>', value,
        )
    if isinstance(value, bool):
        return format_html(
            '<i class="bi {}"></i>',
            "bi-check-circle-fill text-ok" if value else "bi-dash-circle text-muted",
        )
    if isinstance(value, datetime):
        return timezone.localtime(value).strftime("%d %b %Y %H:%M") if timezone.is_aware(value) else value.strftime("%d %b %Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d %b %Y")
    if isinstance(value, Decimal):
        currency = current_currency_code() or settings.CURRENCY
        return f"{currency} {value:,.2f}"
    return value


@register.filter
def money(value):
    try:
        currency = current_currency_code() or settings.CURRENCY
        return f"{currency} {Decimal(value):,.2f}"
    except Exception:
        return "—"
