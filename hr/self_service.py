"""Employee self-service screens: leave, overtime, payslips, news and complaints."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.access import get_membership

from .forms import MyComplaintForm, MyLeaveForm, MyOvertimeForm
from .models import CompanyNews, Employee, EmployeeComplaint, LeaveRequest, OvertimeEntry, Payroll, leave_settings


def _my_employee(request):
    membership = get_membership(request.user)
    if not membership:
        return None
    return Employee._base_manager.filter(user_id=request.user.pk, company_id=membership.company_id).exclude(status="terminated").first()


@login_required
def my_leave(request):
    emp = _my_employee(request)
    if emp is None:
        messages.info(request, "Your account isn't linked to an active employee record in this company yet. Ask HR or your administrator.")
        return redirect("dashboard")
    form = MyLeaveForm(request.POST or None, employee=emp)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        LeaveRequest.objects.create(company_id=emp.company_id, employee=emp, leave_type=d["leave_type"],
                                    start_date=d["start_date"], end_date=d["end_date"], reason=d["reason"], status="pending")
        messages.success(request, f"Leave request sent for approval ({d['days']} working day{'s' if d['days'] != 1 else ''}).")
        return redirect("myspace:leave")
    cfg = leave_settings(emp.company)
    return render(request, "hr/my_leave.html", {
        "emp": emp, "form": form,
        "requests": LeaveRequest.objects.filter(employee=emp)[:20],
        "per_month": cfg["DAYS_PER_MONTH"],
        "counted_types": ", ".join(dict(LeaveRequest.TYPES)[t].lower() for t in cfg["DEDUCT_TYPES"] if t in dict(LeaveRequest.TYPES)),
    })


@login_required
@require_POST
def my_leave_cancel(request, pk):
    emp = _my_employee(request)
    lr = get_object_or_404(LeaveRequest, pk=pk, employee=emp) if emp else None
    if lr and lr.status == "pending":
        lr.delete()
        messages.success(request, "Leave request cancelled.")
    else:
        messages.error(request, "Only your own pending requests can be cancelled.")
    return redirect("myspace:leave")


@login_required
def my_overtime(request):
    emp = _my_employee(request)
    if emp is None:
        messages.info(request, "Your account isn't linked to an active employee record in this company yet.")
        return redirect("dashboard")
    form = MyOvertimeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        entry = OvertimeEntry(company_id=emp.company_id, employee=emp, date=d["date"], hours=d["hours"], reason=d["reason"])
        entry.save()
        messages.success(request, "Overtime submitted to HR for review. The hourly rate and payroll amount are set by HR policy.")
        return redirect("myspace:overtime")
    return render(request, "hr/my_overtime.html", {
        "emp": emp, "form": form,
        "entries": OvertimeEntry.objects.filter(employee=emp)[:30],
    })


@login_required
def my_payslips(request):
    emp = _my_employee(request)
    if emp is None:
        messages.info(request, "Your account isn't linked to an active employee record in this company yet.")
        return redirect("dashboard")
    payslips = Payroll.objects.filter(employee=emp, status="paid").order_by("-period")
    return render(request, "hr/my_payslips.html", {"emp": emp, "payslips": payslips})


@login_required
def my_payslip_detail(request, pk):
    emp = _my_employee(request)
    if emp is None:
        return redirect("dashboard")
    payroll = get_object_or_404(Payroll, pk=pk, employee=emp, status="paid")
    return render(request, "hr/my_payslip_detail.html", {"emp": emp, "payroll": payroll})


@login_required
def my_news(request):
    membership = get_membership(request.user)
    emp = _my_employee(request)
    if not membership:
        return redirect("dashboard")
    news = CompanyNews.objects.filter(is_published=True)
    if emp and emp.department_id:
        news = news.filter(Q(department__isnull=True) | Q(department_id=emp.department_id))
    else:
        news = news.filter(department__isnull=True)
    return render(request, "hr/my_news.html", {"news_items": news, "emp": emp})


@login_required
def my_complaints(request):
    membership = get_membership(request.user)
    if not membership:
        return redirect("dashboard")
    emp = _my_employee(request)
    form = MyComplaintForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        complaint = form.save(commit=False)
        complaint.company_id = membership.company_id
        if complaint.anonymous:
            complaint.employee = None  # deliberately do not retain account/employee identity
        else:
            if emp is None:
                form.add_error(None, "Your account has no employee record. Submit anonymously or ask HR to link your account.")
                return render(request, "hr/my_complaints.html", {"form": form, "complaints": EmployeeComplaint.objects.none()})
            complaint.employee = emp
        complaint.save()
        messages.success(request, f"Complaint submitted. Keep reference {complaint.number} to quote when following up.")
        return redirect("myspace:complaints")
    complaints = EmployeeComplaint.objects.filter(employee=emp) if emp else EmployeeComplaint.objects.none()
    return render(request, "hr/my_complaints.html", {"form": form, "complaints": complaints[:20]})
