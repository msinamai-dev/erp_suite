from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from core.models import CompanyOwned, Numbered, money
from sales.models import Customer, Product

class StockMovement(Numbered):
    PREFIX = "STK"
    TYPES = [("receipt", "Stock received"), ("sale", "Sale/dispatch"), ("return", "Customer return"), ("adjustment_in", "Positive adjustment"), ("adjustment_out", "Negative adjustment")]
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    movement_date = models.DateField(default=timezone.localdate)
    movement_type = models.CharField(max_length=16, choices=TYPES)
    quantity = models.PositiveIntegerField()
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    class Meta: ordering = ["-movement_date", "-id"]
    def clean(self):
        super().clean()
        if not self.product_id or not self.quantity:
            return
        product = Product.objects.filter(pk=self.product_id).first()
        if not product:
            raise ValidationError({"product": "Choose a product belonging to the active company."})
        current_qty = product.stock_qty
        old = type(self)._base_manager.filter(pk=self.pk).first() if self.pk else None
        if old and old.product_id == product.pk:
            old_delta = old.quantity if old.movement_type in ("receipt", "return", "adjustment_in") else -old.quantity
            current_qty -= old_delta
        delta = self.quantity if self.movement_type in ("receipt", "return", "adjustment_in") else -self.quantity
        if current_qty + delta < 0:
            raise ValidationError({"quantity": "This movement would make stock negative."})
    def save(self, *args, **kwargs):
        # Apply stock once when a new movement is created. Edits are disallowed at the view level by policy.
        with transaction.atomic():
            old = type(self)._base_manager.filter(pk=self.pk).first() if self.pk else None
            product_ids = {self.product_id}
            if old:
                product_ids.add(old.product_id)
            products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=product_ids)}
            def delta(kind, quantity):
                return quantity if kind in ("receipt", "return", "adjustment_in") else -quantity
            if old:
                # Reverse the old movement, then apply the edited movement atomically.
                previous = products[old.product_id]
                previous.stock_qty -= delta(old.movement_type, old.quantity)
                if previous.stock_qty < 0:
                    raise ValueError("Cannot edit this movement because it would make stock negative.")
                current = products[self.product_id]
                current.stock_qty += delta(self.movement_type, self.quantity)
                if current.stock_qty < 0:
                    raise ValueError("This movement would make stock negative.")
                for product in products.values():
                    product.save(update_fields=["stock_qty"])
            else:
                product = products[self.product_id]
                product.stock_qty += delta(self.movement_type, self.quantity)
                if product.stock_qty < 0:
                    raise ValueError("This movement would make stock negative.")
                product.save(update_fields=["stock_qty"])
            super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        raise ProtectedError("Stock movements are part of the inventory audit trail. Use a return or adjustment instead.", self)
    def __str__(self): return f"{self.number or 'Movement'} - {self.product}"

class RetailSale(Numbered):
    PREFIX = "POS"
    STATUS = [("draft", "Draft"), ("completed", "Completed"), ("void", "Voided")]
    CHANNELS = [("retail", "Retail"), ("wholesale", "Wholesale")]
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.PROTECT)
    sale_date = models.DateTimeField(default=timezone.now)
    channel = models.CharField(max_length=12, choices=CHANNELS, default="retail")
    payment_method = models.CharField(max_length=20, choices=[("cash", "Cash"), ("card", "Card"), ("transfer", "Bank transfer"), ("credit", "Credit")], default="cash")
    reference = models.CharField(max_length=100, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = money(default=0)
    discount_amount = money(default=0)
    total = money(default=0, editable=False)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    stock_applied = models.BooleanField(default=False, editable=False)
    notes = models.TextField(blank=True)
    class Meta: ordering = ["-sale_date", "-id"]
    def clean(self):
        super().clean()
        old = type(self)._base_manager.filter(pk=self.pk).first() if self.pk else None
        if old and old.stock_applied and (old.product_id != self.product_id or old.quantity != self.quantity or old.status != self.status):
            raise ValidationError("A sale that has affected stock cannot be edited. Create a return or stock adjustment instead.")
        if self.status == "completed" and not self.stock_applied and self.product_id:
            product = Product.objects.filter(pk=self.product_id).first()
            if not product:
                raise ValidationError({"product": "Choose a product belonging to the active company."})
            if product.stock_qty < self.quantity:
                raise ValidationError({"quantity": "Insufficient stock to complete this sale."})
    def save(self, *args, **kwargs):
        self.total = max(Decimal("0"), Decimal(self.quantity) * Decimal(self.unit_price) - Decimal(self.discount_amount))
        with transaction.atomic():
            if self.pk:
                old = type(self)._base_manager.filter(pk=self.pk).first()
                if old and old.stock_applied and (old.product_id != self.product_id or old.quantity != self.quantity or old.status != self.status):
                    raise ValueError("A sale that has affected stock cannot be edited. Create a return or stock adjustment instead.")
            if self.status == "completed" and not self.stock_applied:
                product = Product.objects.select_for_update().get(pk=self.product_id)
                if product.stock_qty < self.quantity:
                    raise ValueError("Insufficient stock to complete this sale.")
                product.stock_qty -= self.quantity
                product.save(update_fields=["stock_qty"])
                self.stock_applied = True
            super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        if self.stock_applied:
            raise ProtectedError("This completed sale has affected stock. Use a return or adjustment instead.", self)
        return super().delete(*args, **kwargs)
    def __str__(self): return self.number or "New retail sale"
