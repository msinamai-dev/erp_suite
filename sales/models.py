from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models import CompanyOwned, Numbered, money


class Customer(CompanyOwned):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(CompanyOwned):
    sku = models.CharField("SKU", max_length=40)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=80, blank=True)
    unit_price = money()
    stock_qty = models.PositiveIntegerField("stock on hand", default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "sku"], name="uniq_product_sku_per_company")]

    def __str__(self):
        return f"{self.sku} - {self.name}"


class SalesOrder(Numbered):
    PREFIX = "SO"
    STATUS = [("draft", "Draft"), ("confirmed", "Confirmed"),
              ("delivered", "Delivered"), ("cancelled", "Cancelled")]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    order_date = models.DateField(default=timezone.localdate)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = money()
    discount_pct = models.DecimalField("discount %", max_digits=5, decimal_places=2, default=0)
    total = money(editable=False, default=0)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")

    class Meta:
        ordering = ["-order_date", "-id"]
        verbose_name = "sales order"

    def save(self, *args, **kwargs):
        gross = Decimal(self.quantity) * Decimal(self.unit_price)
        self.total = (gross * (Decimal(100) - Decimal(self.discount_pct)) / Decimal(100)).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number or "New sales order"
