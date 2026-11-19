import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.access import get_membership

from .forms import PaymentForm
from .models import Account, Invoice, Payment
from .utils import amount_in_words

ZERO = Decimal("0")


@login_required
def trial_balance(request):
    rows, total_dr, total_cr = [], ZERO, ZERO
    for acc in Account.objects.annotate(dr=Sum("entries__debit"), cr=Sum("entries__credit")).order_by("code"):
        dr, cr = acc.dr or ZERO, acc.cr or ZERO
        net = dr - cr
        rows.append({"account": acc, "debit": dr, "credit": cr,
                     "dr_balance": net if net > 0 else ZERO,
                     "cr_balance": -net if net < 0 else ZERO})
        total_dr += rows[-1]["dr_balance"]
        total_cr += rows[-1]["cr_balance"]
    return render(request, "accounting/trial_balance.html", {
        "rows": rows, "total_dr": total_dr, "total_cr": total_cr,
        "balanced": total_dr == total_cr,
    })


# --------------------------------------------------------------------- invoices
def _invoice_qs():
    return Invoice.objects.select_related("customer", "sales_order", "sales_order__product")


@login_required
def invoice_detail(request, pk):
    Invoice.refresh_overdue()
    inv = get_object_or_404(_invoice_qs(), pk=pk)
    return render(request, "accounting/invoice_detail.html", {
        "invoice": inv,
        "payments": inv.payments.all(),
        "can_send": inv.status == "draft",
        "can_pay": inv.status in ("sent", "overdue") and inv.balance > 0,
        "can_cancel": inv.status in ("draft", "sent", "overdue") and inv.amount_paid == 0,
    })


@login_required
def invoice_print(request, pk):
    """Clean A4 invoice (no sidebar). Use the browser's Print dialog to print or 'Save as PDF'."""
    inv = get_object_or_404(_invoice_qs(), pk=pk)
    so = inv.sales_order
    if so:
        lines = [{"desc": so.product.name, "sub": f"SKU {so.product.sku} · Order {so.number}",
                  "qty": so.quantity, "price": so.unit_price, "disc": so.discount_pct, "total": so.total}]
        diff = inv.amount - so.total
        if diff:
            lines.append({"desc": "Adjustment / other charges", "sub": "", "qty": 1,
                          "price": diff, "disc": ZERO, "total": diff})
    else:
        lines = [{"desc": "Goods / services supplied", "sub": "", "qty": 1,
                  "price": inv.amount, "disc": ZERO, "total": inv.amount}]

    # Invoice branding and tax settings come from the invoice's own company record, never
    # global environment defaults, so each tenant controls its own address and VAT setup.
    membership = get_membership(request.user)
    co = inv.company or (membership.company if membership else None)
    company_name = co.name if co else "Company"
    profile = {
        "address": co.address if co else "",
        "postal_address": co.postal_address if co else "",
        "phone": co.phone if co else "",
        "email": co.email if co else "",
        "tax_id": ((co.vat_number if co.vat_registered else co.registration_number) or "") if co else "",
        "bank": co.bank_details if co else "",
        "terms": co.invoice_terms if co else "",
    }
    vat_rate = Decimal(str(co.vat_rate if co and co.vat_registered else 0))
    net = vat = None
    if vat_rate > 0:
        # Current invoice totals are VAT-inclusive in this version of the invoice model.
        net = (inv.amount / (Decimal("1") + vat_rate / Decimal("100"))).quantize(Decimal("0.01"))
        vat = inv.amount - net

    stamps = {"paid": ("PAID", "ok"), "overdue": ("OVERDUE", "bad"),
              "draft": ("DRAFT", "grey"), "cancelled": ("CANCELLED", "grey")}
    return render(request, "accounting/invoice_print.html", {
        "invoice": inv,
        "lines": lines,
        "payments": inv.payments.all(),
        "profile": profile,
        "company": company_name,
        "vat_rate": vat_rate, "net": net, "vat": vat,
        "terms_days": (inv.due_date - inv.issue_date).days,
        "words": amount_in_words(inv.amount, co.currency_name if co else ""),
        "stamp": stamps.get(inv.status),
    })


@login_required
def invoice_pay(request, pk):
    inv = get_object_or_404(Invoice.objects.select_related("customer"), pk=pk)
    detail = reverse("accounting:invoice_detail", args=[inv.pk])
    if inv.status not in ("sent", "overdue") or inv.balance <= 0:
        messages.error(request, "Payments can only be recorded against sent invoices with a balance.")
        return redirect(detail)
    form = PaymentForm(request.POST or None, instance=Payment(invoice=inv),
                       initial={"date": timezone.localdate(), "amount": inv.balance})
    if request.method == "POST" and form.is_valid():
        payment = form.save()
        messages.success(request, f"Payment {payment.number} recorded for {inv.number}.")
        return redirect(detail)
    return render(request, "core/form.html", {
        "form": form, "title": f"Invoice {inv.number}", "singular": "payment", "list_url": detail,
    })


@login_required
@require_POST
def invoice_set_status(request, pk, status):
    inv = get_object_or_404(Invoice, pk=pk)
    if status == "sent" and inv.status == "draft":
        inv.status = "sent"
        inv.status = inv.computed_status()  # may already be overdue
        msg = f"{inv.number} marked as sent."
    elif status == "cancelled" and inv.status != "cancelled" and inv.amount_paid == 0:
        inv.status = "cancelled"
        msg = f"{inv.number} cancelled."
    else:
        messages.error(request, "That status change isn't allowed for this invoice.")
        return redirect("accounting:invoice_detail", pk=inv.pk)
    inv.save()
    messages.success(request, msg)
    return redirect("accounting:invoice_detail", pk=inv.pk)


@login_required
def invoice_export(request):
    """CSV of invoices (honours the list's search box), opens cleanly in Excel."""
    Invoice.refresh_overdue()
    qs = Invoice.objects.select_related("customer").order_by("-issue_date", "-id")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(customer__name__icontains=q))
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="invoices-{timezone.localdate():%Y-%m-%d}.csv"'
    response.write("\ufeff")
    w = csv.writer(response)
    w.writerow(["Invoice", "Customer", "Issue date", "Due date", "Amount", "Paid", "Balance", "Status", "Days overdue"])
    for i in qs:
        w.writerow([i.number, i.customer.name, i.issue_date.isoformat(), i.due_date.isoformat(),
                    i.amount, i.amount_paid, i.balance, i.get_status_display(), i.days_overdue])
    return response


# --------------------------------------------------------------------- reports
BUCKETS = ["Not yet due", "1–30 days", "31–60 days", "61–90 days", "Over 90 days"]


@login_required
def ageing_report(request):
    """Accounts receivable ageing: outstanding invoice balances by customer and days past due."""
    Invoice.refresh_overdue()
    today = timezone.localdate()
    by_customer = {}
    totals = [ZERO] * 5
    open_invoices = (Invoice.objects.exclude(status__in=["draft", "cancelled", "paid"])
                     .select_related("customer"))
    for inv in open_invoices:
        bal = inv.balance
        if bal <= 0:
            continue
        days = (today - inv.due_date).days
        idx = 0 if days <= 0 else 1 if days <= 30 else 2 if days <= 60 else 3 if days <= 90 else 4
        row = by_customer.setdefault(inv.customer_id, {"customer": inv.customer, "cells": [ZERO] * 5,
                                                       "total": ZERO, "count": 0})
        row["cells"][idx] += bal
        row["total"] += bal
        row["count"] += 1
        totals[idx] += bal
    rows = sorted(by_customer.values(), key=lambda r: r["total"], reverse=True)
    grand = sum(totals, ZERO)
    return render(request, "accounting/ageing.html", {
        "rows": rows, "buckets": BUCKETS, "totals": totals, "grand": grand, "as_at": today,
        "overdue_total": sum(totals[1:], ZERO),
        "overdue_pct": round(sum(totals[1:], ZERO) * 100 / grand) if grand else 0,
    })


@login_required
def dashboard(request):
    """Finance overview inspired by established small-business accounting suites."""
    from .models import Expense, JournalEntry
    Invoice.refresh_overdue()
    invoices = Invoice.objects.exclude(status__in=["draft", "cancelled"])
    open_invoices = invoices.exclude(status="paid")
    receivables = sum((inv.balance for inv in open_invoices), ZERO)
    overdue = sum((inv.balance for inv in open_invoices if inv.due_date < timezone.localdate()), ZERO)
    collected = Payment.objects.aggregate(total=Sum("amount"))["total"] or ZERO
    expenses = Expense.objects.exclude(status="rejected").aggregate(total=Sum("amount"))["total"] or ZERO
    revenue_lines = JournalEntry.objects.filter(account__account_type="revenue").aggregate(credits=Sum("credit"), debits=Sum("debit"))
    revenue = (revenue_lines["credits"] or ZERO) - (revenue_lines["debits"] or ZERO)
    return render(request, "accounting/dashboard.html", {
        "receivables": receivables, "overdue": overdue, "collected": collected,
        "expenses_total": expenses, "revenue": revenue,
        "open_invoice_count": open_invoices.count(),
        "overdue_count": open_invoices.filter(due_date__lt=timezone.localdate()).count(),
        "recent_invoices": Invoice.objects.select_related("customer")[:6],
        "recent_payments": Payment.objects.select_related("invoice", "invoice__customer")[:5],
    })


@login_required
def profit_loss(request):
    """Income statement from posted general-ledger journal lines for a selected period."""
    from .models import JournalEntry
    today = timezone.localdate()
    try:
        start = timezone.datetime.strptime(request.GET.get("start", f"{today.year}-01-01"), "%Y-%m-%d").date()
    except ValueError:
        start = today.replace(month=1, day=1)
    try:
        end = timezone.datetime.strptime(request.GET.get("end", today.isoformat()), "%Y-%m-%d").date()
    except ValueError:
        end = today
    rows = []
    totals = {"revenue": ZERO, "expense": ZERO}
    entries = JournalEntry.objects.filter(date__gte=start, date__lte=end).select_related("account")
    accounts = Account.objects.filter(account_type__in=["revenue", "expense"]).order_by("account_type", "code")
    for account in accounts:
        lines = entries.filter(account=account).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        debit, credit = lines["debit"] or ZERO, lines["credit"] or ZERO
        amount = credit - debit if account.account_type == "revenue" else debit - credit
        if amount:
            rows.append({"account": account, "amount": amount})
            totals[account.account_type] += amount
    return render(request, "accounting/profit_loss.html", {
        "rows": rows, "start": start, "end": end, "revenue_total": totals["revenue"],
        "expense_total": totals["expense"], "net_profit": totals["revenue"] - totals["expense"],
    })


@login_required
def balance_sheet(request):
    """Statement of financial position based on posted ledger balances."""
    from .models import JournalEntry
    as_at = request.GET.get("as_at", timezone.localdate().isoformat())
    try:
        as_date = timezone.datetime.strptime(as_at, "%Y-%m-%d").date()
    except ValueError:
        as_date = timezone.localdate()
    rows = {"asset": [], "liability": [], "equity": []}
    totals = {"asset": ZERO, "liability": ZERO, "equity": ZERO}
    accounts = Account.objects.filter(account_type__in=rows).order_by("account_type", "code")
    for account in accounts:
        sums = JournalEntry.objects.filter(account=account, date__lte=as_date).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        debit, credit = sums["debit"] or ZERO, sums["credit"] or ZERO
        balance = debit - credit if account.account_type == "asset" else credit - debit
        if balance:
            rows[account.account_type].append({"account": account, "code": account.code, "name": account.name, "balance": balance})
            totals[account.account_type] += balance
    # Include unclosed cumulative earnings in equity so the statement reflects the result of P&L accounts.
    income = JournalEntry.objects.filter(date__lte=as_date, account__account_type="revenue").aggregate(debit=Sum("debit"), credit=Sum("credit"))
    costs = JournalEntry.objects.filter(date__lte=as_date, account__account_type="expense").aggregate(debit=Sum("debit"), credit=Sum("credit"))
    revenue_net = (income["credit"] or ZERO) - (income["debit"] or ZERO)
    expense_net = (costs["debit"] or ZERO) - (costs["credit"] or ZERO)
    earnings = revenue_net - expense_net
    if earnings:
        rows["equity"].append({"account": None, "code": "", "name": "Unclosed cumulative earnings", "balance": earnings})
        totals["equity"] += earnings
    return render(request, "accounting/balance_sheet.html", {
        "rows": rows, "totals": totals, "as_at": as_date,
        "balanced": totals["asset"].quantize(Decimal("0.01")) == (totals["liability"] + totals["equity"]).quantize(Decimal("0.01")),
    })
