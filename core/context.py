from django.conf import settings
from django.urls import reverse

from accounts.access import allowed_module_keys, get_membership, is_company_admin, user_memberships
from accounts.models import Company

from .navigation import MODULES


def erp(request):
    """Sidebar data: every module, with items expanded for the module being viewed."""
    rm = getattr(request, "resolver_match", None)
    ns = rm.namespace if rm else ""
    name = rm.url_name if rm else ""
    user = getattr(request, "user", None)
    allowed = allowed_module_keys(user) if user is not None else set()
    membership = get_membership(user) if user is not None else None
    my_employee = None
    if membership is not None and membership.company.is_approved:
        from hr.models import Employee

        my_employee = Employee._base_manager.filter(user_id=user.pk, company_id=membership.company_id).exclude(status="terminated").first()
    company = membership.company if membership else None
    available_companies = user_memberships(user) if user is not None and getattr(user, "is_authenticated", False) else []
    mods = []
    for m in MODULES:
        if allowed is not None and m["key"] not in allowed:
            continue
        active = m["key"] == ns
        items = []
        if active:
            for i in m["items"]:
                base = i["url"].rsplit("_", 1)[0]
                items.append({
                    **i,
                    "href": reverse(f"{i.get('namespace', m['key'])}:{i['url']}"),
                    "active": name == i["url"] or name.startswith(base + "_"),
                })
        mods.append({**m, "active": active, "home": reverse(f"{m['key']}:home"), "items": items})
    return {
        "MODULES": mods,
        "COMPANY": company.name if company else settings.COMPANY_NAME,
        "CURRENCY": company.currency_code if company else settings.CURRENCY,
        "company_brand": company,
        "available_companies": available_companies,
        "active_company_id": company.pk if company else None,
        "user_company": company,
        "my_employee": my_employee,
        "my_leave_balance": my_employee.leave_balance if my_employee else 0,
        "is_company_admin": is_company_admin(user) if user is not None else False,
        "pending_companies": (Company.objects.filter(is_approved=False).count()
                              if user is not None and user.is_superuser else 0),
        "active_module": next((m for m in mods if m["active"]), None),
    }
