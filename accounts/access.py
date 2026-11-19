"""Company membership and module access for the active company workspace."""
from django.db.models import Q
from .models import Membership


def get_membership(user):
    if not getattr(user, "is_authenticated", False):
        return None
    active_company_id = getattr(user, "_erp_active_company_id", None)
    cache_key = f"_erp_membership_{active_company_id or 'default'}"
    if not hasattr(user, cache_key):
        qs = Membership.objects.select_related("company").filter(user_id=user.pk)
        if active_company_id:
            qs = qs.filter(company_id=active_company_id)
        membership = qs.order_by("company__name").first()
        setattr(user, cache_key, membership)
    return getattr(user, cache_key)


def user_memberships(user):
    if not getattr(user, "is_authenticated", False):
        return Membership.objects.none()
    return Membership.objects.filter(user_id=user.pk, company__is_approved=True).select_related("company").order_by("company__name")


def allowed_module_keys(user):
    """None = unrestricted system owner; otherwise only active-company modules are returned."""
    if getattr(user, "is_superuser", False):
        return None
    m = get_membership(user)
    if not m or not m.company.is_approved:
        return set()
    company_keys = set(m.company.modules.values_list("key", flat=True))
    if m.role == "admin":
        return company_keys
    allowed = company_keys & set(m.modules.values_list("key", flat=True))
    if "pos_bridge" in company_keys and allowed.intersection({"retail", "sales"}):
        allowed.add("pos_bridge")
    # Department heads and explicitly delegated initiators/approvers need the requisition workspace
    # even when procurement is not their home department. The company must have enabled procurement.
    if "procurement" in company_keys:
        if m.position == "hod":
            allowed.add("procurement")
        else:
            try:
                from procurement.models import RequisitionAuthority
                if RequisitionAuthority.objects.filter(
                    Q(can_initiate=True) | Q(can_approve=True), company=m.company, membership=m
                ).exists():
                    allowed.add("procurement")
            except (ImportError, RuntimeError):
                pass
    return allowed


def is_company_admin(user):
    m = get_membership(user)
    return bool(m and m.role == "admin" and m.company.is_approved)
