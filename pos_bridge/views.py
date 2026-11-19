from datetime import timedelta
import base64, hashlib, hmac, json, os, secrets
from urllib.parse import urlencode
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.access import get_membership, is_company_admin
from .forms import POSLinkRequestForm
from .models import POSShopLink, POSLinkRequest, POSLinkAudit, POSShop, POSBranch, POSProduct, POSCategory, POSTransaction, POSSalesItem, POSPurchaseOrder, POSStockHistory, POSExpense, POSShift


def _scope(request):
    membership = get_membership(request.user)
    if not membership or not membership.company.is_approved:
        raise PermissionDenied("Your account is not linked to an approved ERP company.")
    if not is_company_admin(request.user) and not membership.modules.filter(key__in=["retail", "sales"]).exists():
        raise PermissionDenied("Ask your company administrator to grant you Retail or Sales access.")
    return membership, POSShopLink.objects.filter(company=membership.company, active=True)


def _filtered(qs, link):
    qs = qs.filter(shop_id=link.shop_id)
    return qs.filter(branch_id=link.branch_id) if link.branch_id else qs


def _paginate(request, queryset, default=15):
    try:
        per_page = int(request.GET.get("page_size", default))
    except (TypeError, ValueError):
        per_page = default
    if per_page not in (10, 15):
        per_page = default
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    params = request.GET.copy()
    params.pop("page", None)
    query_string = params.urlencode()
    return page_obj, per_page, query_string


def _unavailable(request):
    return render(request, "pos_bridge/unavailable.html", status=503)


def _selected_link(request, links):
    rows = list(links)
    selected = next((x for x in rows if str(x.pk) == request.GET.get("link")), None)
    return rows, selected or (rows[0] if rows else None)


@login_required
def home(request):
    membership, links = _scope(request)
    try:
        links, selected = _selected_link(request, links)
        today = timezone.localdate()
        start = today - timedelta(days=6)
        totals = {"today_sales": Decimal("0"), "week_sales": Decimal("0"), "transactions_today": 0,
                  "product_count": 0, "low_stock_count": 0, "returns_count": 0}
        recent, top_products, currency = [], [], ""
        if selected:
            shop = POSShop.objects.using("pos").filter(pk=selected.shop_id).first()
            currency = shop.default_currency if shop else ""
            products = _filtered(POSProduct.objects.using("pos").all(), selected)
            txns = _filtered(POSTransaction.objects.using("pos").all(), selected)
            items = _filtered(POSSalesItem.objects.using("pos").all(), selected)
            totals["product_count"] = products.count()
            totals["low_stock_count"] = products.filter(stock__lte=10, status=True).count()
            totals["today_sales"] = txns.filter(date_added__date=today).aggregate(v=Sum("grand_total"))["v"] or Decimal("0")
            totals["week_sales"] = txns.filter(date_added__date__gte=start, date_added__date__lte=today).aggregate(v=Sum("grand_total"))["v"] or Decimal("0")
            totals["transactions_today"] = txns.filter(date_added__date=today).count()
            totals["returns_count"] = items.filter(type="return").count()
            recent = list(txns.order_by("-date_added").values("id", "code", "receipt_number", "customer_name", "grand_total", "currency", "payment_method", "date_added", "branch_id")[:12])
            branch_ids = {r["branch_id"] for r in recent if r["branch_id"]}
            branch_names = {b.pk: b.name for b in POSBranch.objects.using("pos").filter(pk__in=branch_ids)}
            for row in recent:
                row["branch_name"] = branch_names.get(row["branch_id"], "—")
            item_rows = list(items.filter(type="sale").values("product_id").annotate(quantity=Sum("qty"), sales=Sum("total")).order_by("-quantity")[:8])
            product_map = {p.pk: p.name for p in POSProduct.objects.using("pos").filter(pk__in=[r["product_id"] for r in item_rows])}
            top_products = [{**r, "product_name": product_map.get(r["product_id"], f"Product #{r['product_id']}")} for r in item_rows]
        return render(request, "pos_bridge/home.html", {"links": links, "selected": selected, "totals": totals, "recent": recent, "top_products": top_products, "currency": currency, "start": start, "end": today})
    except DatabaseError:
        return _unavailable(request)


@login_required
def products(request):
    membership, links = _scope(request)
    try:
        links, selected = _selected_link(request, links)
        if not selected:
            return render(request, "pos_bridge/products.html", {"links": links, "selected": None, "rows": [], "q": "", "low_stock": False, "page_obj": None, "per_page": 15, "query_string": ""})
        q = request.GET.get("q", "").strip()
        low_stock = request.GET.get("low_stock") == "1"
        qs = _filtered(POSProduct.objects.using("pos").all(), selected)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
        if low_stock:
            qs = qs.filter(stock__lte=10, status=True)
        page_obj, per_page, query_string = _paginate(request, qs.order_by("name"))
        rows = list(page_obj.object_list)
        category_ids = {p.category_id for p in rows if p.category_id}
        categories = {c.pk: c.name for c in POSCategory.objects.using("pos").filter(pk__in=category_ids)}
        for p in rows:
            p.category_name = categories.get(p.category_id, "—")
        return render(request, "pos_bridge/products.html", {"links": links, "selected": selected, "rows": rows, "q": q, "low_stock": low_stock, "page_obj": page_obj, "per_page": per_page, "query_string": query_string})
    except DatabaseError:
        return _unavailable(request)


@login_required
def transactions(request):
    membership, links = _scope(request)
    try:
        links, selected = _selected_link(request, links)
        if not selected:
            return render(request, "pos_bridge/transactions.html", {"links": links, "selected": None, "rows": [], "q": "", "start": "", "end": "", "page_obj": None, "per_page": 15, "query_string": ""})
        q, start, end = request.GET.get("q", "").strip(), request.GET.get("start", ""), request.GET.get("end", "")
        qs = _filtered(POSTransaction.objects.using("pos").all(), selected)
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(receipt_number__icontains=q) | Q(customer_name__icontains=q))
        if start:
            qs = qs.filter(date_added__date__gte=start)
        if end:
            qs = qs.filter(date_added__date__lte=end)
        page_obj, per_page, query_string = _paginate(request, qs.order_by("-date_added"))
        rows = list(page_obj.object_list)
        branch_ids = {r.branch_id for r in rows if r.branch_id}
        branches = {b.pk: b.name for b in POSBranch.objects.using("pos").filter(pk__in=branch_ids)}
        for row in rows:
            row.branch_name = branches.get(row.branch_id, "—")
        return render(request, "pos_bridge/transactions.html", {"links": links, "selected": selected, "rows": rows, "q": q, "start": start, "end": end, "page_obj": page_obj, "per_page": per_page, "query_string": query_string})
    except DatabaseError:
        return _unavailable(request)


@login_required
def transaction_detail(request, pk):
    membership, links = _scope(request)
    try:
        transaction = POSTransaction.objects.using("pos").filter(pk=pk).first()
        allowed = list(links)
        if not transaction or not any(x.shop_id == transaction.shop_id and (not x.branch_id or x.branch_id == transaction.branch_id) for x in allowed):
            raise PermissionDenied("This POS transaction is outside the shops or branches linked to your ERP company.")
        items = list(POSSalesItem.objects.using("pos").filter(transaction_id=transaction.pk).order_by("id"))
        products = {p.pk: p for p in POSProduct.objects.using("pos").filter(pk__in=[i.product_id for i in items])}
        for item in items:
            product = products.get(item.product_id)
            item.product_name = product.name if product else f"Product #{item.product_id}"
            item.product_code = product.code if product else ""
        branch = POSBranch.objects.using("pos").filter(pk=transaction.branch_id).first() if transaction.branch_id else None
        return render(request, "pos_bridge/transaction_detail.html", {"transaction": transaction, "items": items, "branch": branch})
    except DatabaseError:
        return _unavailable(request)


@login_required
def purchases(request):
    membership, links = _scope(request)
    try:
        links, selected = _selected_link(request, links)
        if not selected:
            return render(request, "pos_bridge/purchases.html", {"links": links, "selected": None, "rows": [], "q": "", "page_obj": None, "per_page": 15, "query_string": ""})
        q = request.GET.get("q", "").strip()
        qs = _filtered(POSPurchaseOrder.objects.using("pos").all(), selected)
        if q:
            lookup = Q(payment_method__icontains=q)
            product_ids = POSProduct.objects.using("pos").filter(Q(name__icontains=q) | Q(code__icontains=q)).values_list("id", flat=True)
            lookup |= Q(product_id__in=product_ids)
            if q.isdigit():
                lookup |= Q(id=int(q)) | Q(product_id=int(q))
            qs = qs.filter(lookup)
        page_obj, per_page, query_string = _paginate(request, qs.order_by("-date"))
        rows = list(page_obj.object_list)
        products = {p.pk: p.name for p in POSProduct.objects.using("pos").filter(pk__in=[r.product_id for r in rows if r.product_id])}
        for row in rows:
            row.product_name = products.get(row.product_id, "—")
        return render(request, "pos_bridge/purchases.html", {"links": links, "selected": selected, "rows": rows, "q": q, "page_obj": page_obj, "per_page": per_page, "query_string": query_string})
    except DatabaseError:
        return _unavailable(request)


@login_required
def stock_history(request):
    membership, links = _scope(request)
    try:
        links, selected = _selected_link(request, links)
        if not selected:
            return render(request, "pos_bridge/stock_history.html", {"links": links, "selected": None, "rows": [], "q": "", "page_obj": None, "per_page": 15, "query_string": ""})
        q = request.GET.get("q", "").strip()
        qs = _filtered(POSStockHistory.objects.using("pos").all(), selected)
        if q:
            product_ids = POSProduct.objects.using("pos").filter(Q(name__icontains=q) | Q(code__icontains=q)).values_list("id", flat=True)
            lookup = Q(product_id__in=product_ids)
            if q.isdigit():
                lookup |= Q(product_id=int(q)) | Q(id=int(q))
            qs = qs.filter(lookup)
        page_obj, per_page, query_string = _paginate(request, qs.order_by("-added_on"))
        rows = list(page_obj.object_list)
        products = {p.pk: p.name for p in POSProduct.objects.using("pos").filter(pk__in=[r.product_id for r in rows])}
        for row in rows:
            row.product_name = products.get(row.product_id, f"Product #{row.product_id}")
        return render(request, "pos_bridge/stock_history.html", {"links": links, "selected": selected, "rows": rows, "q": q, "page_obj": page_obj, "per_page": per_page, "query_string": query_string})
    except DatabaseError:
        return _unavailable(request)


@login_required
def expenses(request):
    membership, links = _scope(request)
    try:
        links, selected = _selected_link(request, links)
        if not selected:
            return render(request, "pos_bridge/expenses.html", {"links": links, "selected": None, "expenses": [], "shifts": [], "q": "", "page_obj": None, "shift_page": None, "per_page": 15, "query_string": ""})
        q = request.GET.get("q", "").strip()
        expense_qs = _filtered(POSExpense.objects.using("pos").all(), selected)
        shift_qs = _filtered(POSShift.objects.using("pos").all(), selected)
        if q:
            expense_lookup = Q(reason__icontains=q)
            if q.isdigit():
                expense_lookup |= Q(id=int(q))
                shift_qs = shift_qs.filter(Q(id=int(q)) | Q(branch_id=int(q)))
            expense_qs = expense_qs.filter(expense_lookup)
        expense_page, per_page, query_string = _paginate(request, expense_qs.order_by("-created_at"))
        shift_page, _, _ = _paginate(request, shift_qs.order_by("-opened_at"))
        expense_rows = list(expense_page.object_list)
        shift_rows = list(shift_page.object_list)
        return render(request, "pos_bridge/expenses.html", {"links": links, "selected": selected, "expenses": expense_rows, "shifts": shift_rows, "q": q, "page_obj": expense_page, "shift_page": shift_page, "per_page": per_page, "query_string": query_string})
    except DatabaseError:
        return _unavailable(request)


def _link_secret():
    return os.environ.get("POS_LINK_SHARED_SECRET", "").encode("utf-8")


def _signed_payload(payload):
    secret = _link_secret()
    if len(secret) < 32:
        raise RuntimeError("Set POS_LINK_SHARED_SECRET to the same strong random value (at least 32 characters) in both ERP and POS settings.")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    signature = hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return encoded + "." + signature


def _verify_callback(values):
    secret = _link_secret()
    signature = values.pop("signature", "")
    raw = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(secret, raw, hashlib.sha256).hexdigest() if len(secret) >= 32 else ""
    return bool(len(secret) >= 32 and signature and hmac.compare_digest(signature, expected))


@login_required
def shop_links(request):
    membership = get_membership(request.user)
    if not membership or not is_company_admin(request.user):
        raise PermissionDenied("Only a company administrator can request a POS shop link.")
    expired_requests = POSLinkRequest.objects.filter(company=membership.company, status=POSLinkRequest.Status.PENDING, expires_at__lte=timezone.now())
    for expired_request in expired_requests:
        expired_request.status = POSLinkRequest.Status.EXPIRED
        expired_request.save(update_fields=["status"])
        POSLinkAudit.objects.create(company=membership.company, request=expired_request, shop_id=expired_request.shop_id,
            event="link_expired", actor=None, actor_label="system", details={"reason": "approval window elapsed"})
    form = POSLinkRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            secret = _link_secret()
            if not secret:
                messages.error(request, "POS linking is not configured yet. Set POS_LINK_SHARED_SECRET in both projects.")
                return redirect("pos_bridge:shop_links")
            shop_id = int(form.cleaned_data["shop_id"])
            shop = POSShop.objects.using("pos").filter(pk=shop_id, is_active=True).first()
            if not shop:
                messages.error(request, "That POS shop is no longer active.")
                return redirect("pos_bridge:shop_links")
            existing_assignment = POSShopLink.objects.filter(shop_id=shop_id).first()
            if existing_assignment and (existing_assignment.company_id != membership.company_id or existing_assignment.active):
                messages.error(request, "This shop is already assigned to an ERP company. A transfer must be explicitly approved before reassignment.")
                return redirect("pos_bridge:shop_links")
            expiry = timezone.now() + timedelta(minutes=20)
            with transaction.atomic():
                link_request = POSLinkRequest.objects.create(
                    company=membership.company,
                    shop_id=shop_id,
                    shop_name=shop.name,
                    branch_id=int(form.cleaned_data["branch_id"]) if form.cleaned_data.get("branch_id") else None,
                    requested_by=request.user,
                    expires_at=expiry,
                )
                POSLinkAudit.objects.create(company=membership.company, request=link_request, shop_id=shop_id,
                    event="link_requested", actor=request.user, actor_label=request.user.get_username(),
                    details={"shop_name": shop.name, "branch_id": link_request.branch_id})
            erp_base = os.environ.get("ERP_PUBLIC_BASE_URL", request.build_absolute_uri("/").rstrip("/"))
            callback = erp_base.rstrip("/") + reverse("pos_bridge:owner_callback")
            payload = {
                "request_id": str(link_request.pk), "company_id": membership.company.pk,
                "company_name": membership.company.name, "shop_id": shop_id, "shop_name": shop.name,
                "requested_by": request.user.get_username(), "branch_id": link_request.branch_id, "expires_at": int(expiry.timestamp()),
                "return_url": callback, "nonce": secrets.token_urlsafe(18),
            }
            token = _signed_payload(payload)
            pos_base = os.environ.get("POS_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
            approval_url = pos_base + "/erp-link/authorize/?" + urlencode({"token": token})
            messages.info(request, "Link request created. The POS shop owner must sign in and approve it before access is activated.")
            return redirect(approval_url)
        except DatabaseError:
            messages.error(request, "The POS database could not be reached. Check the POS DB settings.")
        except RuntimeError as exc:
            messages.error(request, str(exc))
    links = POSShopLink.objects.filter(company=membership.company).order_by("-created_at")
    requests = POSLinkRequest.objects.filter(company=membership.company).select_related("requested_by")[:30]
    return render(request, "pos_bridge/shop_links.html", {"form": form, "links": links, "requests": requests})


@login_required
def owner_callback(request):
    if request.method != "GET":
        return HttpResponseBadRequest("Invalid callback method.")
    values = {k: request.GET.get(k, "") for k in ("request_id", "company_id", "shop_id", "decision", "pos_user_id", "approved_at")}
    signature = request.GET.get("signature", "")
    signed = dict(values)
    signed["signature"] = signature
    if not _verify_callback(signed):
        return HttpResponseBadRequest("POS approval signature is invalid.")
    try:
        link_request = POSLinkRequest.objects.select_related("company").get(pk=values["request_id"])
    except (POSLinkRequest.DoesNotExist, ValueError):
        return HttpResponseBadRequest("Link request not found.")
    if link_request.status != POSLinkRequest.Status.PENDING:
        messages.warning(request, "This link request has already been processed.")
        return redirect("pos_bridge:shop_links")
    if link_request.expires_at <= timezone.now():
        link_request.status = POSLinkRequest.Status.EXPIRED
        link_request.save(update_fields=["status"])
        POSLinkAudit.objects.create(company=link_request.company, request=link_request, shop_id=link_request.shop_id,
            event="link_expired", actor=request.user, actor_label=request.user.get_username())
        messages.error(request, "This link request expired. Please create a new request.")
        return redirect("pos_bridge:shop_links")
    if str(link_request.company_id) != values["company_id"] or str(link_request.shop_id) != values["shop_id"]:
        return HttpResponseBadRequest("Approval does not match this request.")
    if values["decision"] == "approved":
        existing = POSShopLink.objects.filter(shop_id=link_request.shop_id).first()
        if existing and existing.company_id != link_request.company_id:
            link_request.status = POSLinkRequest.Status.REJECTED
            link_request.save(update_fields=["status"])
            POSLinkAudit.objects.create(company=link_request.company, request=link_request, shop_id=link_request.shop_id,
                event="mapping_conflict", actor=None, actor_label=f"POS user #{values['pos_user_id']} approved; mapping conflict",
                details={"existing_company_id": existing.company_id})
            messages.error(request, "The owner approved the request, but this shop is already assigned to another ERP company. Resolve the existing assignment first.")
            return redirect("pos_bridge:shop_links")
        with transaction.atomic():
            shop = POSShop.objects.using("pos").filter(pk=link_request.shop_id).first()
            branch = POSBranch.objects.using("pos").filter(pk=link_request.branch_id).first() if link_request.branch_id else None
            label = f"{shop.name} — {branch.name}" if shop and branch else (shop.name if shop else link_request.shop_name)
            if existing:
                existing.branch_id = link_request.branch_id
                existing.label = label
                existing.active = True
                existing.created_by = link_request.requested_by
                existing.save(update_fields=["branch_id", "label", "active", "created_by"])
            else:
                POSShopLink.objects.create(company=link_request.company, shop_id=link_request.shop_id,
                    branch_id=link_request.branch_id, label=label, active=True, created_by=link_request.requested_by)
            link_request.status = POSLinkRequest.Status.APPROVED
            link_request.approved_at = parse_datetime(values["approved_at"]) or timezone.now()
            link_request.approved_pos_user_id = int(values["pos_user_id"])
            link_request.save(update_fields=["status", "approved_at", "approved_pos_user_id"])
            POSLinkAudit.objects.create(company=link_request.company, request=link_request, shop_id=link_request.shop_id,
                event="link_approved_and_activated", actor=None,
                actor_label=f"POS user #{values['pos_user_id']}", details={"shop_name": link_request.shop_name})
        messages.success(request, f"Shop {link_request.shop_name} is now linked to {link_request.company.name}.")
    elif values["decision"] == "rejected":
        link_request.status = POSLinkRequest.Status.REJECTED
        link_request.approved_pos_user_id = int(values["pos_user_id"])
        link_request.save(update_fields=["status", "approved_pos_user_id"])
        POSLinkAudit.objects.create(company=link_request.company, request=link_request, shop_id=link_request.shop_id,
            event="link_rejected", actor=None, actor_label=f"POS user #{values['pos_user_id']}")
        messages.warning(request, "The POS owner rejected the shop-link request.")
    else:
        return HttpResponseBadRequest("Unknown approval decision.")
    return redirect("pos_bridge:shop_links")

@login_required
@require_POST
def delete_shop_link(request, pk):
    membership = get_membership(request.user)
    if not membership or not is_company_admin(request.user):
        raise PermissionDenied("Only a company administrator can remove POS shop and branch links.")
    link = get_object_or_404(POSShopLink, pk=pk, company=membership.company)
    POSLinkAudit.objects.create(company=membership.company, shop_id=link.shop_id, event="mapping_revoked",
        actor=request.user, actor_label=request.user.get_username(), details={"label": link.label, "branch_id": link.branch_id})
    link.delete()
    messages.success(request, "POS access mapping revoked. The POS records themselves were not changed.")
    return redirect("pos_bridge:shop_links")
