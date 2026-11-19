from django.urls import path

from core.crud import crud_urls, module_home

from .models import Lease, MaintenanceRequest, Property, Unit

app_name = "estates"

urlpatterns = [path("", module_home, name="home")]
urlpatterns += crud_urls(Property, "property", ["name", "property_type", "city", "units", "value", "status"],
                         "Properties", search=["name", "city", "address"])
urlpatterns += crud_urls(Unit, "unit", ["property", "unit_number", "floor", "area_sqm", "monthly_rent", "status"],
                         "Units", search=["unit_number", "property__name"])
urlpatterns += crud_urls(Lease, "lease",
                         ["number", "unit", "tenant_name", "start_date", "end_date", "monthly_rent", "status"],
                         "Leases", search=["number", "tenant_name", "unit__unit_number", "unit__property__name"])
urlpatterns += crud_urls(MaintenanceRequest, "maintenance",
                         ["number", "property", "unit", "title", "priority", "cost", "status"],
                         "Maintenance", search=["number", "title", "property__name"])
