from django.urls import path

from core.crud import crud_urls, module_home

from .models import Asset, SoftwareLicense, Ticket

app_name = "it_ops"

urlpatterns = [path("", module_home, name="home")]
urlpatterns += crud_urls(Asset, "asset",
                         ["number", "name", "category", "serial_number", "assigned_to", "warranty_expiry", "status"],
                         "Assets", search=["number", "name", "serial_number", "assigned_to__first_name"])
urlpatterns += crud_urls(Ticket, "ticket",
                         ["number", "title", "requested_by", "assigned_to", "priority", "status", "created_at"],
                         "Support tickets", search=["number", "title", "assigned_to"])
urlpatterns += crud_urls(SoftwareLicense, "license", ["name", "vendor", "seats", "cost", "expiry_date"],
                         "Software licences", search=["name", "vendor"])
