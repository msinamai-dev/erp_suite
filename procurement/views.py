from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.access import get_membership
from accounts.models import Membership
from .access import (can_approve_requisition, can_initiate_in, initiable_department_ids,
                     is_company_admin, is_procurement_staff, visible_requisitions)
from .forms import RequisitionAuthorityForm
from .models import (GoodsReceipt, PurchaseOrder, Requisition, RequisitionAuthority,
                     RequestForQuotation, Supplier, SupplierQuote)


@login_required
def dashboard(request):
    membership = get_membership(request.user)
    if not membership or not membership.company.is_approved:
        raise PermissionDenied("You do not have an active company account.")
    all_reqs = visible_requisitions(request.user, Requisition.objects.all())
    pending_reqs = all_reqs.filter(status="pending")
    approval_reqs = [r for r in pending_reqs.select_related("department", "requested_by", "created_by", "project")
                     if can_approve_requisition(request.user, r) and
                     (is_company_admin(request.user) or r.created_by_id != request.user.pk)]
    procurement_staff = is_procurement_staff(request.user)
    open_rfq = RequestForQuotation.objects.filter(status="open") if procurement_staff else RequestForQuotation.objects.none()
    active_orders = PurchaseOrder.objects.filter(status="ordered") if procurement_staff else PurchaseOrder.objects.none()
    spend = (PurchaseOrder.objects.exclude(status="cancelled").aggregate(total=Sum("total"))["total"] or Decimal("0")) if procurement_staff else Decimal("0")
    context = {
        "pending_requisitions": len(approval_reqs),
        "open_rfqs": open_rfq.count(),
        "active_orders": active_orders.count(),
        "active_suppliers": Supplier.objects.filter(is_active=True).count() if procurement_staff else 0,
        "committed_spend": spend,
        "recent_requisitions": approval_reqs[:6],
        "recent_orders": PurchaseOrder.objects.select_related("supplier")[:6] if procurement_staff else [],
        "closing_rfqs": RequestForQuotation.objects.filter(status__in=["draft", "open", "closed"]).order_by("closing_date")[:5] if procurement_staff else [],
        "can_initiate": bool(initiable_department_ids(request.user)),
        "is_procurement_staff": procurement_staff,
        "can_manage_delegations": bool(is_company_admin(request.user) or membership.position == "hod"),
    }
    return render(request, "procurement/dashboard.html", context)


@login_required
def delegations(request):
    membership = get_membership(request.user)
    if not membership or not membership.company.is_approved:
        raise PermissionDenied("You do not have an active company account.")
    if not (is_company_admin(request.user) or membership.position == "hod"):
        raise PermissionDenied("Only a company administrator or HOD can delegate requisition permissions.")
    form = RequisitionAuthorityForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        authority = form.save(commit=False)
        existing = RequisitionAuthority.objects.filter(company=membership.company,
                    department=authority.department, membership=authority.membership).first()
        if existing:
            existing.can_initiate = authority.can_initiate
            existing.can_approve = authority.can_approve
            existing.granted_by = membership
            if not existing.can_initiate and not existing.can_approve:
                existing.delete()
            else:
                existing.save()
        else:
            authority.save()
        messages.success(request, "Department requisition permissions updated.")
        return redirect("procurement:delegations")
    authorities = RequisitionAuthority.objects.filter(company=membership.company).select_related(
        "department", "membership__user", "granted_by__user")
    if not is_company_admin(request.user):
        allowed_ids = [d.pk for d in membership.modules.all()]
        authorities = authorities.filter(department_id__in=allowed_ids)
    staff_by_department = {}
    for department in form.fields["department"].queryset:
        staff = Membership.objects.filter(
            company=membership.company, role="member", user__is_active=True, modules=department
        ).select_related("user").distinct().order_by("user__first_name", "user__last_name", "user__username")
        staff_by_department[str(department.pk)] = [
            {"id": row.pk, "label": row.user.get_full_name() or row.user.username}
            for row in staff
        ]
    return render(request, "procurement/delegations.html", {
        "form": form, "authorities": authorities, "company": membership.company,
        "staff_by_department": staff_by_department,
        "selected_membership": request.POST.get("membership", ""),
    })


@login_required
@require_POST
def requisition_action(request, pk, action):
    req = get_object_or_404(Requisition, pk=pk)
    if action not in ("approve", "reject") or req.status != "pending":
        messages.error(request, "Only pending requisitions can be approved or rejected.")
    elif not can_approve_requisition(request.user, req):
        raise PermissionDenied("Only the department HOD or a delegate with approval permission can approve this requisition.")
    elif req.created_by_id == request.user.pk and not is_company_admin(request.user):
        raise PermissionDenied("You cannot approve your own requisition. Ask another authorized approver.")
    else:
        req.status = "approved" if action == "approve" else "rejected"
        if action == "approve":
            req.approved_by = request.user
            req.approved_at = timezone.now()
            req.save(update_fields=["status", "approved_by", "approved_at"])
        else:
            req.save(update_fields=["status"])
        messages.success(request, f"Requisition {req.number} {req.get_status_display().lower()}.")
    return redirect("procurement:requisition_list")


@login_required
@require_POST
def order_action(request, pk, action):
    if not is_procurement_staff(request.user):
        raise PermissionDenied("Only authorized procurement staff can issue or cancel purchase orders.")
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if action == "send" and po.status == "draft":
        po.status = "ordered"
        po.save(update_fields=["status"])
        messages.success(request, f"Purchase order {po.number} issued to {po.supplier.name}.")
    elif action == "cancel" and po.status in ("draft", "ordered") and not po.receipts.exists():
        po.status = "cancelled"
        po.save(update_fields=["status"])
        messages.success(request, f"Purchase order {po.number} cancelled.")
    else:
        messages.error(request, "That purchase order action is not allowed in its current state.")
    return redirect("procurement:purchaseorder_list")


@login_required
@require_POST
def rfq_action(request, pk, action):
    if not is_procurement_staff(request.user):
        raise PermissionDenied("Only authorized procurement staff can manage RFQs and award quotations.")
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    if action == "open" and rfq.status == "draft":
        rfq.status = "open"
        rfq.save(update_fields=["status"])
        messages.success(request, f"{rfq.number} is now open for supplier quotations.")
    elif action == "close" and rfq.status == "open":
        rfq.status = "closed"
        rfq.save(update_fields=["status"])
        messages.success(request, f"{rfq.number} has been closed.")
    elif action == "award" and rfq.status in ("open", "closed"):
        quote = rfq.quotes.filter(status="submitted").select_related("supplier").order_by("quoted_unit_price", "lead_time_days").first()
        if not quote:
            messages.error(request, "There are no submitted supplier quotations to award.")
        elif rfq.requisition.status != "approved":
            messages.error(request, "Approve the linked requisition before awarding a quotation.")
        else:
            po = PurchaseOrder.objects.create(
                supplier=quote.supplier, requisition=rfq.requisition, project=rfq.requisition.project,
                item=rfq.item, quantity=rfq.quantity, unit_cost=quote.quoted_unit_price,
                expected_date=timezone.localdate() + timezone.timedelta(days=quote.lead_time_days), status="draft"
            )
            quote.status = "selected"
            quote.save(update_fields=["status"])
            rfq.quotes.exclude(pk=quote.pk).filter(status="submitted").update(status="rejected")
            rfq.status = "awarded"
            rfq.save(update_fields=["status"])
            rfq.requisition.status = "ordered"
            rfq.requisition.save(update_fields=["status"])
            messages.success(request, f"Quotation awarded to {quote.supplier.name}; draft purchase order {po.number} created for review.")
            return redirect("procurement:purchaseorder_list")
    else:
        messages.error(request, "That RFQ action is not allowed in its current state.")
    return redirect("procurement:rfq_list")
