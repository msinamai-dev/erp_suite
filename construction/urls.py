from django.urls import path

from core.crud import crud_urls, module_home

from .models import Project, ProjectTask, Subcontract

app_name = "construction"

urlpatterns = [path("", module_home, name="home")]
urlpatterns += crud_urls(Project, "project",
                         ["number", "name", "client", "manager", "status", "progress", "budget", "spent"],
                         "Projects", search=["number", "name", "site_location", "client__name"])
urlpatterns += crud_urls(ProjectTask, "task",
                         ["name", "project", "assigned_to", "due_date", "progress", "status"],
                         "Tasks", search=["name", "project__name"])
urlpatterns += crud_urls(Subcontract, "subcontract",
                         ["number", "project", "contractor", "scope", "contract_value", "status"],
                         "Subcontracts", search=["number", "contractor", "project__name"])
