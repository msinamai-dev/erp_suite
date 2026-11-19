from django.urls import path
from core.crud import crud_urls, module_home
from .models import Driver, Vehicle, Trip, DeliveryUpdate, VehicleExpense
app_name = "transport"
urlpatterns = [path("", module_home, name="home")]
urlpatterns += crud_urls(Driver, "driver", ["employee_number", "full_name", "phone", "licence_number", "licence_expiry", "is_active"], "Drivers", search=["employee_number", "full_name", "phone", "licence_number"])
urlpatterns += crud_urls(Vehicle, "vehicle", ["registration", "vehicle_type", "make_model", "capacity_kg", "odometer_km", "insurance_expiry", "active"], "Fleet", search=["registration", "make_model"])
urlpatterns += crud_urls(Trip, "trip", ["number", "vehicle", "driver", "origin", "destination", "planned_departure", "expected_arrival", "status"], "Trips and consignments", search=["number", "reference", "origin", "destination", "cargo_description"])
urlpatterns += crud_urls(DeliveryUpdate, "delivery-update", ["number", "trip", "recorded_at", "location", "status_note", "reported_by"], "Delivery tracking updates", search=["number", "trip__number", "location", "status_note"])
urlpatterns += crud_urls(VehicleExpense, "vehicle-expense", ["number", "vehicle", "date", "expense_type", "description", "quantity", "amount"], "Fleet expenses", search=["number", "vehicle__registration", "description", "receipt_reference"])
