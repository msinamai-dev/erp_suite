from django.conf import settings
from django.db import models
from accounts.models import Company
import uuid


class POSShopLink(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="pos_shop_links")
    shop_id = models.PositiveIntegerField(unique=True, help_text="ID of the shop in the POS database. One ERP company per POS shop.")
    branch_id = models.PositiveIntegerField(null=True, blank=True, help_text="Optional POS branch ID; blank means all branches.")
    label = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["company__name", "label", "shop_id", "branch_id"]

    def __str__(self):
        return self.label or (f"POS shop {self.shop_id}" + (f" / branch {self.branch_id}" if self.branch_id else ""))


class POSLinkRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending owner approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="pos_link_requests")
    shop_id = models.PositiveIntegerField()
    shop_name = models.CharField(max_length=255)
    branch_id = models.PositiveIntegerField(null=True, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pos_link_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_pos_user_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class POSLinkAudit(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL)
    request = models.ForeignKey(POSLinkRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events")
    shop_id = models.PositiveIntegerField(null=True, blank=True)
    event = models.CharField(max_length=50)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    actor_label = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# Read-only unmanaged mirrors of tables in the separate POS database.
class POSShop(models.Model):
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    default_currency = models.CharField(max_length=3, blank=True)
    location = models.CharField(max_length=255, blank=True)
    class Meta:
        managed = False
        db_table = "posApp_shop"


class POSBranch(models.Model):
    id = models.BigIntegerField(primary_key=True)
    shop_id = models.BigIntegerField()
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        managed = False
        db_table = "posApp_branch"


class POSProduct(models.Model):
    id = models.BigIntegerField(primary_key=True)
    shop_id = models.BigIntegerField()
    branch_id = models.BigIntegerField(null=True)
    category_id = models.BigIntegerField(null=True)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=100, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cprice = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    unit = models.CharField(max_length=20, null=True, blank=True)
    status = models.BooleanField(default=True)
    date_updated = models.DateTimeField(null=True)
    class Meta:
        managed = False
        db_table = "posApp_products"


class POSCategory(models.Model):
    id = models.BigIntegerField(primary_key=True)
    shop_id = models.BigIntegerField()
    branch_id = models.BigIntegerField(null=True)
    name = models.TextField()
    class Meta:
        managed = False
        db_table = "posApp_category"


class POSTransaction(models.Model):
    id = models.BigIntegerField(primary_key=True)
    shop_id = models.BigIntegerField(null=True)
    branch_id = models.BigIntegerField(null=True)
    code = models.CharField(max_length=100)
    receipt_number = models.CharField(max_length=50, null=True, blank=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inclusive_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    exclusive_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date_added = models.DateTimeField()
    currency = models.CharField(max_length=3, default="USD")
    payment_method = models.CharField(max_length=20, blank=True)
    user_id = models.BigIntegerField(null=True)
    shift_id = models.BigIntegerField(null=True)
    class Meta:
        managed = False
        db_table = "posApp_transaction"


class POSSalesItem(models.Model):
    id = models.BigIntegerField(primary_key=True)
    transaction_id = models.BigIntegerField()
    product_id = models.BigIntegerField()
    shop_id = models.BigIntegerField(null=True)
    branch_id = models.BigIntegerField(null=True)
    qty = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    type = models.CharField(max_length=20, default="sale")
    class Meta:
        managed = False
        db_table = "posApp_salesitem"


class POSPurchaseOrder(models.Model):
    id = models.BigIntegerField(primary_key=True)
    shop_id = models.BigIntegerField(null=True)
    branch_id = models.BigIntegerField(null=True)
    product_id = models.BigIntegerField(null=True)
    quantity = models.IntegerField(default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    date = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, null=True, blank=True)
    class Meta:
        managed = False
        db_table = "posApp_purchaseorder"


class POSStockHistory(models.Model):
    id = models.BigIntegerField(primary_key=True)
    product_id = models.BigIntegerField()
    shop_id = models.BigIntegerField(null=True)
    branch_id = models.BigIntegerField(null=True)
    previous_stock = models.IntegerField(default=0)
    quantity_added = models.IntegerField(default=0)
    quantity_removed = models.IntegerField(default=0)
    new_stock = models.IntegerField(default=0)
    added_on = models.DateTimeField()
    class Meta:
        managed = False
        db_table = "posApp_stockhistory"


class POSExpense(models.Model):
    id = models.BigIntegerField(primary_key=True)
    shop_id = models.BigIntegerField()
    branch_id = models.BigIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    class Meta:
        managed = False
        db_table = "posApp_expense"


class POSShift(models.Model):
    id = models.BigIntegerField(primary_key=True)
    shop_id = models.BigIntegerField()
    branch_id = models.BigIntegerField()
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_money = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    is_closed = models.BooleanField(default=False)
    class Meta:
        managed = False
        db_table = "posApp_shift"
