from decimal import Decimal
from django.db import models
from django.utils import timezone
from core.models import CompanyOwned, Numbered, money

class Grower(CompanyOwned):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=180)
    national_id = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    contract_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="uniq_grower_code_company")]
    def __str__(self): return f"{self.code} - {self.name}"

class TobaccoLot(Numbered):
    PREFIX = "LOT"
    STATUS = [("received", "Received"), ("graded", "Graded"), ("settled", "Settled"), ("rejected", "Rejected")]
    grower = models.ForeignKey(Grower, on_delete=models.PROTECT)
    season = models.CharField(max_length=30, default="")
    received_date = models.DateField(default=timezone.localdate)
    bale_count = models.PositiveIntegerField(default=0)
    gross_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    tare_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    net_weight_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0, editable=False)
    status = models.CharField(max_length=12, choices=STATUS, default="received")
    notes = models.TextField(blank=True)
    class Meta: ordering = ["-received_date", "-id"]
    def save(self, *args, **kwargs):
        self.net_weight_kg = max(Decimal("0"), Decimal(self.gross_weight_kg) - Decimal(self.tare_weight_kg))
        super().save(*args, **kwargs)
    def __str__(self): return self.number or "New tobacco lot"

class WeighingTicket(Numbered):
    PREFIX = "WT"
    lot = models.ForeignKey(TobaccoLot, on_delete=models.PROTECT)
    weighed_at = models.DateTimeField(default=timezone.now)
    gross_kg = models.DecimalField(max_digits=12, decimal_places=3)
    tare_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    net_kg = models.DecimalField(max_digits=12, decimal_places=3, default=0, editable=False)
    scale_operator = models.CharField(max_length=120, blank=True)
    scale_reference = models.CharField(max_length=80, blank=True)
    class Meta: ordering = ["-weighed_at"]
    def save(self, *args, **kwargs):
        self.net_kg = max(Decimal("0"), Decimal(self.gross_kg) - Decimal(self.tare_kg))
        super().save(*args, **kwargs)
    def __str__(self): return self.number or "New weighing ticket"

class TobaccoGrade(CompanyOwned):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price_per_kg = money(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="uniq_tobacco_grade_company")]
    def __str__(self): return f"{self.code} - {self.name}"

class GradeRecord(Numbered):
    PREFIX = "GR"
    lot = models.ForeignKey(TobaccoLot, on_delete=models.PROTECT)
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.PROTECT)
    weight_kg = models.DecimalField(max_digits=12, decimal_places=3)
    assessed_by = models.CharField(max_length=120, blank=True)
    assessed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    @property
    def estimated_value(self): return Decimal(self.weight_kg) * Decimal(self.grade.price_per_kg)
    class Meta: ordering = ["-assessed_at"]
    def __str__(self): return f"{self.number or 'New grade'} - {self.grade}"

class GrowerSettlement(Numbered):
    PREFIX = "SET"
    STATUS = [("draft", "Draft"), ("approved", "Approved"), ("paid", "Paid"), ("cancelled", "Cancelled")]
    grower = models.ForeignKey(Grower, on_delete=models.PROTECT)
    lot = models.ForeignKey(TobaccoLot, on_delete=models.PROTECT)
    settlement_date = models.DateField(default=timezone.localdate)
    gross_amount = money(default=0)
    deductions = money(default=0)
    net_amount = money(default=0, editable=False)
    payment_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    notes = models.TextField(blank=True)
    class Meta: ordering = ["-settlement_date", "-id"]
    def save(self, *args, **kwargs):
        self.net_amount = max(Decimal("0"), Decimal(self.gross_amount) - Decimal(self.deductions))
        super().save(*args, **kwargs)
    def __str__(self): return self.number or "New settlement"
