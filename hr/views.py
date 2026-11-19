from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.access import is_company_admin

from .models import Employee, LeaveRequest, Payroll, month_end


@login_required
def employee_detail(request, pk):
    emp = get_object_or_404(Employee.objects.select_related("department", "user"), pk=pk)
    return render(request, "hr/employee_detail.html", {
        "emp": emp,
        "statuses": Employee.STATUS,
        "leaves": emp.leaverequest_set.all()[:8],
        "payrolls": emp.payroll_set.all()[:6],
        "last_admin": emp.blocks_termination(),
    })


@login_required
@require_POST
def employee_set_status(request, pk, status):
    emp = get_object_or_404(Employee, pk=pk)
    if status not in dict(Employee.STATUS):
        messages.error(request, "Unknown status.")
    elif status == "terminated" and emp.blocks_termination():
        messages.error(request, f"{emp.full_name} is the only active administrator of the company. "
                                "Make someone else an administrator first.")
    else:
        emp.status = status
        emp.save()
        extra = " Their sign-in is switched off." if status == "terminated" and emp.user_id else ""
        messages.success(request, f"{emp.full_name} is now {emp.get_status_display().lower()}.{extra}")
    return redirect("hr:employee_detail", pk=emp.pk)


@login_required
def leave_detail(request, pk):
    lr = get_object_or_404(LeaveRequest.objects.select_related("employee"), pk=pk)
    return render(request, "hr/leave_detail.html", {"lr": lr, "emp": lr.employee})


@login_required
@require_POST
def leave_decide(request, pk, decision):
    lr = get_object_or_404(LeaveRequest.objects.select_related("employee"), pk=pk)
    emp = lr.employee
    if decision not in ("approve", "reject") or lr.status != "pending":
        messages.error(request, "Only pending requests can be approved or rejected.")
    elif emp.user_id == request.user.pk and not (is_company_admin(request.user) or request.user.is_superuser):
        messages.error(request, "You can't approve your own leave. Ask a colleague in HR or an administrator.")
    elif decision == "approve" and lr.uses_allowance and lr.days > emp.leave_balance:
        messages.error(request, f"{emp.full_name} only has {max(emp.leave_balance, 0)} leave day(s) left "
                                f"but this request needs {lr.days}.")
    else:
        lr.status = "approved" if decision == "approve" else "rejected"
        lr.save()
        messages.success(request, f"Leave {lr.get_status_display().lower()} for {emp.full_name}.")
    return redirect("hr:leave_detail", pk=lr.pk)


@login_required
def payroll_generate(request):
    """Add every current employee to the payroll of a chosen month (skips people already on it)."""
    today = timezone.localdate()
    if request.method == "POST":
        try:
            year, month = (int(x) for x in request.POST.get("month", "").split("-"))
            period = month_end(date(year, month, 1))
        except ValueError:
            messages.error(request, "Pick a month.")
            return redirect("hr:payroll_generate")
        added = skipped = 0
        for emp in Employee.objects.exclude(status="terminated"):
            if Payroll.ensure_for(emp, on=period):
                added += 1
            else:
                skipped += 1
        messages.success(request, f"Payroll for {period:%B %Y}: {added} line(s) added, {skipped} already there or not yet hired.")
        return redirect("hr:payroll_list")
    return render(request, "hr/payroll_generate.html", {
        "default_month": f"{today:%Y-%m}",
        "eligible": Employee.objects.exclude(status="terminated").count(),
    })
