from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from core.navigation import MODULES
from core.tenancy import NO_ACCESS, reset_company_id, reset_currency_code, set_company_id, set_currency_code

from .access import allowed_module_keys, get_membership

MODULE_LABELS = {m["key"]: m["label"] for m in MODULES}
EXEMPT_URL_NAMES = {"logout", "login", "register", "switch_company"}


class CompanyAccessMiddleware:
    """Signed-in users must belong to an approved company and may only open their departments."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Everything the view, templates and forms query is limited to this company for the whole request.
        user = getattr(request, "user", None)
        active_membership = None
        if user is not None and user.is_authenticated and not user.is_superuser:
            from .models import Membership
            selected = request.session.get("active_company_id")
            membership_qs = Membership.objects.filter(user_id=user.pk, company__is_approved=True)
            membership = membership_qs.filter(company_id=selected).first() if selected else None
            if membership is None:
                membership = membership_qs.order_by("company__name").first()
                if membership:
                    request.session["active_company_id"] = membership.company_id
                else:
                    request.session.pop("active_company_id", None)
            user._erp_active_company_id = membership.company_id if membership else None
        active_membership = get_membership(user) if user is not None and user.is_authenticated and not user.is_superuser else None
        token = set_company_id(self._company_scope(request))
        currency_token = set_currency_code(active_membership.company.currency_code if active_membership else None)
        if active_membership:
            request.company = active_membership.company
        try:
            return self.get_response(request)
        finally:
            reset_currency_code(currency_token)
            reset_company_id(token)

    @staticmethod
    def _company_scope(request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated or user.is_superuser:
            return None  # superusers (the system owner) see every company
        membership = get_membership(user)
        return membership.company_id if membership else NO_ACCESS  # fail closed

    def process_exception(self, request, exception):
        """Show a friendly permission page instead of Django's technical 403 screen."""
        if not isinstance(exception, PermissionDenied):
            return None
        message = str(exception).strip() or "Your account is not authorized to perform this action."
        return render(request, "accounts/blocked.html", {
            "icon": "bi-shield-lock",
            "heading": "You don't have permission to do that",
            "message": message,
        }, status=403)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        match = request.resolver_match
        if not user.is_authenticated or user.is_superuser or match is None:
            return None
        if match.url_name in EXEMPT_URL_NAMES:
            return None

        membership = get_membership(user)
        if membership is None:
            return render(request, "accounts/blocked.html", {
                "icon": "bi-person-x", "heading": "Your account isn't linked to a company",
                "message": "Ask your company administrator, or the system owner, to add you to a company.",
            }, status=403)
        if not membership.company.is_approved:
            return render(request, "accounts/blocked.html", {
                "icon": "bi-hourglass-split", "heading": "Registration received",
                "message": f"{membership.company.name} is waiting for approval. "
                           "You'll be able to use the system as soon as it has been approved.",
            })
        if match.namespace in MODULE_LABELS and match.namespace not in allowed_module_keys(user):
            return render(request, "accounts/blocked.html", {
                "icon": "bi-lock", "heading": f"No access to {MODULE_LABELS[match.namespace]}",
                "message": "Your account isn't set up for this department. Ask your company administrator to add it.",
            }, status=403)
        return None
