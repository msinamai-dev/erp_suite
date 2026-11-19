import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import CompanyOwned, Numbered, money


def leave_settings(company=None):
    """Use the active company's frontend-configured leave policy, with safe defaults for legacy records."""
    defaults = {"DAYS_PER_MONTH": 3, "DEDUCT_TYPES": ["annual"]}
    if company is not None:
        return {"DAYS_PER_MONTH": company.leave_days_per_month,
                "DEDUCT_TYPES": company.leave_deduct_types or ["annual"]}
    return {**defaults, **getattr(settings, "LEAVE", {})}


def working_days(start, end):
    """Monday-Friday days between two dates, inclusive."""
    if end < start:
        return 0
    total = (end - start).days + 1
    full_weeks, extra = divmod(total, 7)
    days = full_weeks * 5
    first_extra = start + timedelta(days=full_weeks * 7)
    return days + sum(1 for i in range(extra) if (first_extra + timedelta(days=i)).weekday() < 5)


def month_end(day):
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


class Department(CompanyOwned):
    name = models.CharField(max_length=120)
    head_name = models.CharField("department head", max_length=120, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="uniq_department_name_per_company")]

    def __str__(self):
        return self.name


class Employee(Numbered):
    PREFIX = "EMP"
    STATUS = [("active", "Active"), ("on_leave", "On leave"), ("terminated", "Terminated")]

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)
    job_title = models.CharField(max_length=120)
    hire_date = models.DateField(default=timezone.localdate)
    salary = money(verbose_name="monthly salary")
    status = models.CharField(max_length=12, choices=STATUS, default="active")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="employee", limit_choices_to={"employee__isnull": True},
                                verbose_name="sign-in account",
                                help_text="Links this person to a login so they can request leave and see their balance. "
                                          "Terminating the employee also switches the login off.")
    leave_start = models.DateField("leave accrues from", null=True, blank=True,
                                   help_text="Leave starts building up from this date. Leave blank to use the hire date.")

    class Meta:
        ordering = ["first_name", "last_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    # ---- leave allowance: LEAVE["DAYS_PER_MONTH"] days are earned every month and carried over until used
    @property
    def leave_accrued(self):
        start, today = self.leave_start or self.hire_date, timezone.localdate()
        months = 0 if start > today else (today.year - start.year) * 12 + today.month - start.month + 1
        return months * leave_settings(self.company)["DAYS_PER_MONTH"]

    def _leave_days(self, status):
        rows = (LeaveRequest._base_manager
                .filter(employee_id=self.pk, status=status, leave_type__in=leave_settings(self.company)["DEDUCT_TYPES"])
                .values_list("start_date", "end_date"))
        return sum(working_days(a, b) for a, b in rows)

    @property
    def leave_used(self):
        return self._leave_days("approved")

    @property
    def leave_pending(self):
        return self._leave_days("pending")

    @property
    def leave_balance(self):
        """Earned minus approved leave taken: the days still left."""
        return self.leave_accrued - self.leave_used

    @property
    def leave_available(self):
        """Balance after setting aside days already requested and waiting for approval."""
        return self.leave_balance - self.leave_pending

    # ---- status side effects
    def blocks_termination(self):
        """True if this person's login is the last active administrator of their company."""
        from accounts.models import Membership

        if not self.user_id:
            return False
        m = Membership.objects.filter(user_id=self.user_id, role="admin").first()
        return bool(m and not Membership.objects.filter(company_id=m.company_id, role="admin", user__is_active=True)
                    .exclude(pk=m.pk).exists())

    def _sync_login(self):
        """Terminated staff can't sign in; reinstating them switches the login back on."""
        if not self.user_id:
            return
        active = self.status != "terminated"
        if not active and self.blocks_termination():
            return
        get_user_model()._default_manager.filter(pk=self.user_id).update(is_active=active)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        self._sync_login()
        if creating:
            Payroll.ensure_for(self)  # every new person appears on this month's payroll straight away

    def __str__(self):
        return self.full_name


class LeaveRequest(CompanyOwned):
    TYPES = [("annual", "Annual"), ("sick", "Sick"), ("maternity", "Maternity / paternity"),
             ("study", "Study"), ("unpaid", "Unpaid")]
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=12, choices=TYPES, default="annual")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")

    class Meta:
        ordering = ["-start_date"]

    @property
    def days(self):
        """Working days (Mon-Fri) covered by the request."""
        return working_days(self.start_date, self.end_date)

    @property
    def uses_allowance(self):
        return self.leave_type in leave_settings(self.employee.company)["DEDUCT_TYPES"]

    def __str__(self):
        return f"{self.employee} ({self.start_date})"


class Payroll(CompanyOwned):
    STATUS = [("pending", "Pending"), ("paid", "Paid")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period = models.DateField("pay period (month end)")
    basic = money()
    allowances = money(default=0)
    overtime = money(default=0)
    bonus = money(default=0)
    deductions = money(default=0)
    net_pay = money(editable=False, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")

    class Meta:
        ordering = ["-period", "employee__first_name"]
        verbose_name_plural = "payroll"

    @classmethod
    def ensure_for(cls, employee, on=None):
        """Add the employee to the payroll of the month containing `on` (default: this month), once."""
        period = month_end(on or timezone.localdate())
        if employee.status == "terminated" or employee.hire_date > period:
            return None
        if cls._base_manager.filter(employee_id=employee.pk, period__year=period.year,
                                    period__month=period.month).exists():
            return None
        start = date(period.year, period.month, 1)
        overtime_total = sum((row.hours * row.hourly_rate for row in OvertimeEntry._base_manager.filter(
            company_id=employee.company_id, employee=employee, date__range=(start, period), status="approved")), Decimal("0"))
        return cls.objects.create(company_id=employee.company_id, employee=employee, period=period,
                                  basic=employee.salary, overtime=overtime_total, status="pending")

    def save(self, *args, **kwargs):
        self.net_pay = (Decimal(self.basic) + Decimal(self.allowances) + Decimal(self.overtime)
                        + Decimal(self.bonus) - Decimal(self.deductions))
        super().save(*args, **kwargs)
        if self.status == "paid":
            start = date(self.period.year, self.period.month, 1)
            OvertimeEntry._base_manager.filter(company_id=self.company_id, employee_id=self.employee_id,
                                               date__range=(start, self.period), status="approved").update(status="paid")

    def __str__(self):
        return f"{self.employee} - {self.period:%b %Y}"


class OvertimeEntry(CompanyOwned):
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("paid", "Paid")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="overtime_entries")
    date = models.DateField(default=timezone.localdate)
    hours = models.DecimalField(max_digits=7, decimal_places=2)
    hourly_rate = money(default=0, help_text="Rate per hour; set by HR according to company policy.")
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")

    class Meta:
        ordering = ["-date", "employee__first_name"]

    @property
    def amount(self):
        return (self.hours or Decimal("0")) * (self.hourly_rate or Decimal("0"))

    def clean(self):
        errors = {}
        if self.hours is not None and self.hours <= 0:
            errors["hours"] = "Overtime hours must be greater than zero."
        if self.hourly_rate is not None and self.hourly_rate < 0:
            errors["hourly_rate"] = "Hourly rate cannot be negative."
        if self.status == "approved" and (self.hourly_rate is None or self.hourly_rate <= 0):
            errors["hourly_rate"] = "HR must enter a positive hourly rate before approving overtime."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        old = None
        if self.pk:
            old = OvertimeEntry._base_manager.filter(pk=self.pk).values("employee_id", "date", "status").first()
        super().save(*args, **kwargs)
        affected = {(self.employee_id, self.date.year, self.date.month)}
        if old:
            affected.add((old["employee_id"], old["date"].year, old["date"].month))
        for employee_id, year, month in affected:
            period = month_end(date(year, month, 1))
            payroll = Payroll._base_manager.filter(company_id=self.company_id, employee_id=employee_id,
                                                   period=period, status="pending").first()
            if payroll:
                first = date(year, month, 1)
                rows = OvertimeEntry._base_manager.filter(company_id=self.company_id, employee_id=employee_id,
                                                          date__range=(first, period), status="approved")
                payroll.overtime = sum((row.hours * row.hourly_rate for row in rows), Decimal("0"))
                payroll.save()

    def __str__(self):
        return f"{self.employee} · {self.date} · {self.hours}h"


class CompanyNews(CompanyOwned):
    title = models.CharField(max_length=180)
    body = models.TextField()
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   help_text="Leave blank to publish to the whole company.")
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name = "company news item"
        verbose_name_plural = "company news"

    def save(self, *args, **kwargs):
        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class EmployeeComplaint(Numbered):
    PREFIX = "CMP"
    CATEGORIES = [("workplace", "Workplace concern"), ("safety", "Health and safety"),
                  ("harassment", "Harassment or bullying"), ("payroll", "Pay or benefits"),
                  ("management", "Management concern"), ("other", "Other")]
    STATUS = [("new", "New"), ("reviewing", "Under review"), ("resolved", "Resolved"), ("closed", "Closed")]

    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="complaints")
    anonymous = models.BooleanField(default=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="other")
    subject = models.CharField(max_length=180)
    description = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS, default="new")
    submitted_at = models.DateTimeField(auto_now_add=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]
        verbose_name = "employee complaint"

    def save(self, *args, **kwargs):
        if self.anonymous:
            self.employee = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number or 'New complaint'} · {self.subject}"
