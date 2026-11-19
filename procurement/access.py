"""Authorization helpers for company-scoped requisition and procurement workflows."""
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from accounts.access import get_membership
from .models import Requisition, RequisitionAuthority

PROCUREMENT_POSITIONS = {"procurement_officer", "procurement_manager"}


def membership_for(user):
    return get_membership(user)


def is_company_admin(user):
    m = membership_for(user)
    return bool(getattr(user, "is_superuser", False) or (m and m.role == "admin" and m.company.is_approved))


def is_procurement_staff(user):
    if is_company_admin(user):
        return True
    m = membership_for(user)
    return bool(m and m.company.is_approved and m.position in PROCUREMENT_POSITIONS
                and m.modules.filter(key="procurement").exists())


def managed_departments(user):
    """Departments where the user is an HOD or company admin and may delegate authority."""
    m = membership_for(user)
    if not m or not m.company.is_approved:
        return []
    if is_company_admin(user):
        return list(m.company.modules.all())
    if m.position == "hod":
        return list(m.modules.filter(companies=m.company))
    return []


def authority_for(user, department_id=None):
    m = membership_for(user)
    if not m:
        return RequisitionAuthority.objects.none()
    qs = RequisitionAuthority.objects.filter(company_id=m.company_id, membership=m)
    if department_id:
        qs = qs.filter(department_id=department_id)
    return qs


def can_initiate_in(user, department_id):
    if is_company_admin(user):
        return True
    m = membership_for(user)
    if not m or not m.company.is_approved or not department_id:
        return False
    if m.position == "hod" and m.modules.filter(pk=department_id).exists():
        return True
    return authority_for(user, department_id).filter(can_initiate=True).exists()


def can_approve_requisition(user, requisition):
    if is_company_admin(user):
        return True
    m = membership_for(user)
    if not m or not m.company.is_approved or not requisition.department_id:
        return False
    if m.position == "hod" and m.modules.filter(pk=requisition.department_id).exists():
        return True
    return authority_for(user, requisition.department_id).filter(can_approve=True).exists()


def initiable_department_ids(user):
    m = membership_for(user)
    if not m:
        return []
    if is_company_admin(user):
        return list(m.company.modules.values_list("pk", flat=True))
    ids = set(authority_for(user).filter(can_initiate=True).values_list("department_id", flat=True))
    if m.position == "hod":
        ids.update(m.modules.values_list("pk", flat=True))
    return list(ids)


def visible_requisitions(user, queryset=None):
    qs = queryset if queryset is not None else Requisition.objects.all()
    if is_company_admin(user) or is_procurement_staff(user):
        return qs
    m = membership_for(user)
    if not m:
        return qs.none()
    dept_ids = set(m.modules.values_list("pk", flat=True)) if m.position == "hod" else set()
    dept_ids.update(authority_for(user).values_list("department_id", flat=True))
    return qs.filter(Q(department_id__in=dept_ids) | Q(created_by=user)).distinct()


def can_manage_procurement_records(user):
    return is_procurement_staff(user)


def require_procurement_staff(user):
    if not can_manage_procurement_records(user):
        raise PermissionDenied("Only company administrators and authorized procurement staff can manage this procurement stage.")
