from django.urls import path

from . import self_service

app_name = "myspace"

urlpatterns = [
    path("leave/", self_service.my_leave, name="leave"),
    path("leave/<int:pk>/cancel/", self_service.my_leave_cancel, name="leave_cancel"),
    path("overtime/", self_service.my_overtime, name="overtime"),
    path("payslips/", self_service.my_payslips, name="payslips"),
    path("payslips/<int:pk>/", self_service.my_payslip_detail, name="payslip_detail"),
    path("news/", self_service.my_news, name="news"),
    path("complaints/", self_service.my_complaints, name="complaints"),
]
