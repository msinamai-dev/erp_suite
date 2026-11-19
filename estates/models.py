from django.db import models
from django.utils import timezone

from core.models import CompanyOwned, Numbered, money


class Property(CompanyOwned):
    TYPES = [("residential", "Residential"), ("commercial", "Commercial"), ("industrial", "Industrial"),
             ("land", "Land"), ("mixed", "Mixed use")]
    STATUS = [("owned", "Owned"), ("leased_out", "Leased out"), ("development", "Under development"),
              ("for_sale", "For sale")]

    name = models.CharField(max_length=200)
    property_type = models.CharField(max_length=12, choices=TYPES, default="commercial")
    address = models.CharField(max_length=250)
    city = models.CharField(max_length=80, blank=True)
    value = money(verbose_name="book value", default=0)
    status = models.CharField(max_length=12, choices=STATUS, default="owned")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "properties"

    @property
    def units(self):
        return self.unit_set.count()

    def __str__(self):
        return self.name


class Unit(CompanyOwned):
    STATUS = [("available", "Available"), ("occupied", "Occupied"), ("maintenance", "Maintenance")]

    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    unit_number = models.CharField(max_length=20)
    floor = models.PositiveSmallIntegerField(default=0)
    area_sqm = models.PositiveIntegerField("area (m²)", default=0)
    monthly_rent = money()
    status = models.CharField(max_length=12, choices=STATUS, default="available")

    class Meta:
        ordering = ["property__name", "unit_number"]
        unique_together = ("property", "unit_number")

    def __str__(self):
        return f"{self.property} / {self.unit_number}"


class Lease(Numbered):
    PREFIX = "LSE"
    STATUS = [("active", "Active"), ("expired", "Expired"), ("terminated", "Terminated")]

    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    tenant_name = models.CharField(max_length=200)
    tenant_phone = models.CharField(max_length=40, blank=True)
    tenant_email = models.EmailField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = money()
    deposit = money(default=0)
    status = models.CharField(max_length=12, choices=STATUS, default="active")

    class Meta:
        ordering = ["end_date"]

    def __str__(self):
        return f"{self.number} {self.tenant_name}"


class MaintenanceRequest(Numbered):
    PREFIX = "MNT"
    PRIORITY = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]
    STATUS = [("open", "Open"), ("in_progress", "In progress"), ("completed", "Completed")]

    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY, default="medium")
    reported_on = models.DateField(default=timezone.localdate)
    cost = money(default=0)
    status = models.CharField(max_length=12, choices=STATUS, default="open")

    class Meta:
        ordering = ["-reported_on", "-id"]
        verbose_name = "maintenance request"

    def __str__(self):
        return f"{self.number} {self.title}"
