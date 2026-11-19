from django.urls import path

from core.crud import crud_urls, module_home

from . import views
from .models import CompanyNews, Department, Employee, EmployeeComplaint, LeaveRequest, OvertimeEntry, Payroll

app_name = "hr"

urlpatterns = [
    path("", module_home, name="home"),
    path("employee/<int:pk>/", views.employee_detail, name="employee_detail"),
    path("employee/<int:pk>/status/<str:status>/", views.employee_set_status, name="employee_status"),
    path("leave/<int:pk>/", views.leave_detail, name="leave_detail"),
    path("leave/<int:pk>/approve/", views.leave_decide, {"decision": "approve"}, name="leave_approve"),
    path("leave/<int:pk>/reject/", views.leave_decide, {"decision": "reject"}, name="leave_reject"),
    path("payroll/generate/", views.payroll_generate, name="payroll_generate"),
]
urlpatterns += crud_urls(Employee, "employee",
                         ["number", "full_name", "department", "job_title", "hire_date", "salary", "leave_balance", "status"],
                         "Employees", search=["number", "first_name", "last_name", "job_title", "department__name"],
                         row_actions=[("employee_detail", "bi-person-lines-fill", "Profile, leave and status")])
urlpatterns += crud_urls(Department, "department", ["name", "head_name", "description"],
                         "Departments", search=["name", "head_name"])
urlpatterns += crud_urls(LeaveRequest, "leave",
                         ["employee", "leave_type", "start_date", "end_date", "days", "status"],
                         "Leave requests", search=["employee__first_name", "employee__last_name"],
                         row_actions=[("leave_detail", "bi-eye", "Review request")])
urlpatterns += crud_urls(Payroll, "payroll",
                         ["employee", "period", "basic", "allowances", "overtime", "bonus", "deductions", "net_pay", "status"],
                         "Payroll", search=["employee__first_name", "employee__last_name"],
                         list_actions=[("payroll_generate", "bi-magic", "Generate month")])

urlpatterns += crud_urls(OvertimeEntry, "overtime",
                         ["employee", "date", "hours", "hourly_rate", "amount", "reason", "status"],
                         "Overtime", search=["employee__first_name", "employee__last_name", "reason"])
urlpatterns += crud_urls(CompanyNews, "news",
                         ["title", "department", "is_published", "published_at"],
                         "Company news", search=["title", "body"])
urlpatterns += crud_urls(EmployeeComplaint, "complaint",
                         ["number", "anonymous", "category", "subject", "status", "submitted_at"],
                         "Employee complaints", search=["number", "subject", "description"])
