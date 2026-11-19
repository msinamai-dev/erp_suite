from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from accounting.models import Invoice
from accounts.access import allowed_module_keys
from construction.models import Project
from estates.models import Lease, Unit
from hr.models import Employee, LeaveRequest
from it_ops.models import Ticket
from procurement.models import Requisition
from sales.models import SalesOrder


def _six_months(today):
    months, y, m = [], today.year, today.month
    for _ in range(6):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(months))


@login_required
def dashboard(request):
    """Only shows figures from the departments this user is allowed to open."""
    today = timezone.localdate()
    allowed = allowed_module_keys(request.user)  # None = everything

    def can(key):
        return allowed is None or key in allowed

    if can("accounting"):
        Invoice.refresh_overdue()

    kpis, attention = [], []
    if can("sales"):
        revenue = SalesOrder.objects.exclude(status="cancelled").aggregate(t=Sum("total"))["t"] or Decimal("0")
        kpis.append({"label": "Sales revenue", "raw": revenue, "money": True, "icon": "bi-bag-check", "href": reverse("sales:salesorder_list")})
    if can("accounting"):
        receivables = (Invoice.objects.exclude(status__in=["paid", "draft", "cancelled"])
                       .aggregate(t=Sum(F("amount") - F("amount_paid")))["t"] or Decimal("0"))
        kpis.append({"label": "Receivables", "raw": receivables, "money": True, "icon": "bi-hourglass-split", "href": reverse("accounting:invoice_list")})
        attention.append(("Overdue invoices", Invoice.objects.filter(status="overdue").count(), reverse("accounting:invoice_list"), "bi-exclamation-octagon"))
    if can("construction"):
        kpis.append({"label": "Active projects", "raw": Project.objects.filter(status="in_progress").count(), "icon": "bi-cone-striped", "href": reverse("construction:project_list")})
    if can("hr"):
        kpis.append({"label": "Staff on payroll", "raw": Employee.objects.exclude(status="terminated").count(), "icon": "bi-people", "href": reverse("hr:employee_list")})
        attention.append(("Leave requests awaiting approval", LeaveRequest.objects.filter(status="pending").count(), reverse("hr:leave_list"), "bi-calendar2-check"))
    if can("it_ops"):
        kpis.append({"label": "Open IT tickets", "raw": Ticket.objects.filter(status__in=["open", "in_progress"]).count(), "icon": "bi-life-preserver", "href": reverse("it_ops:ticket_list")})
        attention.append(("High-priority IT tickets", Ticket.objects.filter(priority__in=["high", "critical"], status__in=["open", "in_progress"]).count(), reverse("it_ops:ticket_list"), "bi-pc-display-horizontal"))
    if can("estates"):
        units_total = Unit.objects.count()
        units_occupied = Unit.objects.filter(status="occupied").count()
        kpis.append({"label": "Unit occupancy", "raw": f"{round(units_occupied * 100 / units_total) if units_total else 0}%", "icon": "bi-buildings", "href": reverse("estates:unit_list")})
        attention.append(("Leases ending in 60 days", Lease.objects.filter(status="active", end_date__range=(today, today + timedelta(days=60))).count(), reverse("estates:lease_list"), "bi-calendar-event"))
    if can("procurement"):
        attention.append(("Requisitions awaiting approval", Requisition.objects.filter(status="pending").count(), reverse("procurement:requisition_list"), "bi-clipboard-check"))

    sales_chart = project_chart = projects = None
    if can("sales"):
        start = today.replace(day=1) - timedelta(days=155)
        rows = (SalesOrder.objects.exclude(status="cancelled").filter(order_date__gte=start)
                .annotate(m=TruncMonth("order_date")).values("m").annotate(t=Sum("total")))
        by_month = {(r["m"].year, r["m"].month): float(r["t"] or 0) for r in rows}
        months = _six_months(today)
        sales_chart = {"labels": [date(y, m, 1).strftime("%b") for y, m in months],
                       "values": [by_month.get(k, 0) for k in months]}
    if can("construction"):
        status_labels = dict(Project.STATUS)
        proj_rows = Project.objects.values("status").annotate(n=Count("id"))
        project_chart = {"labels": [status_labels.get(r["status"], r["status"]) for r in proj_rows],
                         "values": [r["n"] for r in proj_rows]}
        projects = Project.objects.exclude(status="completed").select_related("client")[:6]

    return render(request, "core/dashboard.html", {
        "kpis": kpis, "attention": attention, "projects": projects,
        "sales_chart": sales_chart, "project_chart": project_chart, "today": today,
    })
