from django.db import models
from django.utils import timezone

from core.models import CompanyOwned, Numbered, money


class Asset(Numbered):
    PREFIX = "AST"
    CATEGORIES = [("laptop", "Laptop"), ("desktop", "Desktop"), ("server", "Server"), ("network", "Network gear"),
                  ("phone", "Phone / tablet"), ("printer", "Printer"), ("other", "Other")]
    STATUS = [("in_stock", "In stock"), ("in_use", "In use"), ("repair", "In repair"), ("retired", "Retired")]

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=10, choices=CATEGORIES, default="laptop")
    serial_number = models.CharField(max_length=80, blank=True)
    assigned_to = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True,
                                    limit_choices_to={"status": "active"})
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    cost = money(default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="in_stock")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.number} {self.name}"


class Ticket(Numbered):
    PREFIX = "TKT"
    PRIORITY = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]
    STATUS = [("open", "Open"), ("in_progress", "In progress"), ("resolved", "Resolved"), ("closed", "Closed")]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    requested_by = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True,
                                     limit_choices_to={"status": "active"})
    assigned_to = models.CharField("assigned technician", max_length=120, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY, default="medium")
    status = models.CharField(max_length=12, choices=STATUS, default="open")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.number} {self.title}"


class SoftwareLicense(CompanyOwned):
    name = models.CharField(max_length=150)
    vendor = models.CharField(max_length=120, blank=True)
    license_key = models.CharField(max_length=200, blank=True)
    seats = models.PositiveIntegerField(default=1)
    cost = money(default=0)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["expiry_date", "name"]
        verbose_name = "software licence"

    def __str__(self):
        return self.name
