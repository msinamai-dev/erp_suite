from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("switch-company/", views.switch_company, name="switch_company"),
    path("team/", views.team_list, name="team"),
    path("team/new/", views.team_create, name="team_create"),
    path("team/<int:pk>/", views.team_edit, name="team_edit"),
    path("company/", views.company_edit, name="company_edit"),
    path("companies/", views.companies, name="companies"),
    path("companies/<int:pk>/toggle/", views.company_toggle, name="company_toggle"),
    path("password/", views.PasswordChange.as_view(), name="password_change"),
]
