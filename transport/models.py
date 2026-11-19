from django.db import models
from django.utils import timezone
from core.models import CompanyOwned, Numbered, money

class Driver(CompanyOwned):
    employee_number = models.CharField(max_length=30)
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40, blank=True)
    licence_number = models.CharField(max_length=60)
    licence_expiry = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ["full_name"]
        constraints = [models.UniqueConstraint(fields=["company", "employee_number"], name="uniq_driver_number_company")]
    def __str__(self): return f"{self.full_name} ({self.employee_number})"

class Vehicle(CompanyOwned):
    VEHICLE_TYPES = [("truck", "Truck"), ("van", "Van"), ("car", "Car"), ("trailer", "Trailer"), ("other", "Other")]
    registration = models.CharField(max_length=30)
    vehicle_type = models.CharField(max_length=12, choices=VEHICLE_TYPES, default="truck")
    make_model = models.CharField(max_length=120, blank=True)
    capacity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    odometer_km = models.PositiveIntegerField(default=0)
    insurance_expiry = models.DateField(null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ["registration"]
        constraints = [models.UniqueConstraint(fields=["company", "registration"], name="uniq_vehicle_reg_company")]
    def __str__(self): return self.registration

class Trip(Numbered):
    PREFIX = "TRIP"
    STATUS = [("planned", "Planned"), ("loading", "Loading"), ("in_transit", "In transit"), ("delivered", "Delivered"), ("delayed", "Delayed"), ("cancelled", "Cancelled")]
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    reference = models.CharField(max_length=80, blank=True, help_text="Link to a sales order, consignment or client reference.")
    origin = models.CharField(max_length=180)
    destination = models.CharField(max_length=180)
    planned_departure = models.DateTimeField(default=timezone.now)
    expected_arrival = models.DateTimeField(null=True, blank=True)
    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)
    cargo_description = models.CharField(max_length=220, blank=True)
    cargo_weight_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    odometer_start_km = models.PositiveIntegerField(null=True, blank=True)
    odometer_end_km = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="planned")
    notes = models.TextField(blank=True)
    class Meta: ordering = ["-planned_departure"]
    def __str__(self): return self.number or "New trip"

class DeliveryUpdate(Numbered):
    PREFIX = "DUP"
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    recorded_at = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=180)
    status_note = models.CharField(max_length=220)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    reported_by = models.CharField(max_length=120, blank=True)
    class Meta: ordering = ["-recorded_at"]
    def __str__(self): return f"{self.trip} — {self.location}"

class VehicleExpense(Numbered):
    PREFIX = "VEX"
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    date = models.DateField(default=timezone.localdate)
    expense_type = models.CharField(max_length=30, choices=[("fuel", "Fuel"), ("service", "Service"), ("repair", "Repair"), ("toll", "Toll"), ("other", "Other")])
    description = models.CharField(max_length=220)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    amount = money(default=0)
    receipt_reference = models.CharField(max_length=80, blank=True)
    class Meta: ordering = ["-date"]
    def __str__(self): return f"{self.number or 'Expense'} - {self.vehicle}"
