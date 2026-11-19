from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.conf import settings

from core.models import CompanyOwned, Numbered, money


class Supplier(CompanyOwned):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    category = models.CharField(max_length=100, blank=True, help_text="e.g. Cement, Steel, Plant hire")
    address = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)],
                                              help_text="1 (poor) to 5 (excellent)")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Requisition(Numbered):
    PREFIX = "REQ"
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("ordered", "Ordered"), ("rejected", "Rejected")]

    item = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    requested_by = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True,
                                     limit_choices_to={"status": "active"})
    project = models.ForeignKey("construction.Project", on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey("accounts.Module", on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="procurement_requisitions")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_requisitions", editable=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="approved_requisitions", editable=False)
    approved_at = models.DateTimeField(null=True, blank=True, editable=False)
    needed_by = models.DateField(null=True, blank=True)
    justification = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")

    class Meta:
        ordering = ["-id"]

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        self._fill_company()
        if self.department_id and self.company_id and not self.company.modules.filter(pk=self.department_id).exists():
            raise ValidationError({"department": "Choose a department enabled for this company."})
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number or self.item


class PurchaseOrder(Numbered):
    PREFIX = "PO"
    STATUS = [("draft", "Draft"), ("ordered", "Ordered"), ("received", "Received"), ("cancelled", "Cancelled")]

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    requisition = models.ForeignKey(Requisition, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey("construction.Project", on_delete=models.SET_NULL, null=True, blank=True)
    item = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_cost = money()
    total = money(editable=False, default=0)
    order_date = models.DateField(default=timezone.localdate)
    expected_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="draft")

    class Meta:
        ordering = ["-order_date", "-id"]
        verbose_name = "purchase order"

    def save(self, *args, **kwargs):
        self.total = (Decimal(self.quantity) * Decimal(self.unit_cost)).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number or self.item


class RequestForQuotation(Numbered):
    """A controlled supplier quotation round linked to an approved business need."""
    PREFIX = "RFQ"
    STATUS = [("draft", "Draft"), ("open", "Open for quotes"), ("closed", "Closed"), ("awarded", "Awarded")]

    title = models.CharField(max_length=200)
    requisition = models.ForeignKey(Requisition, on_delete=models.PROTECT, related_name="rfqs")
    item = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    closing_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-id"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity is not None and self.quantity < 1:
            raise ValidationError({"quantity": "Quantity must be at least one."})
        if self.requisition_id and self.requisition.company_id and self.company_id and self.requisition.company_id != self.company_id:
            raise ValidationError("The RFQ and requisition must belong to the same company.")

    def __str__(self):
        return f"{self.number} - {self.title}"


class SupplierQuote(CompanyOwned):
    STATUS = [("submitted", "Submitted"), ("selected", "Selected"), ("rejected", "Not selected")]
    rfq = models.ForeignKey(RequestForQuotation, on_delete=models.CASCADE, related_name="quotes")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="quotes")
    quoted_unit_price = money()
    lead_time_days = models.PositiveIntegerField(default=0)
    valid_until = models.DateField(null=True, blank=True)
    terms = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="submitted")
    submitted_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["quoted_unit_price", "lead_time_days"]
        constraints = [models.UniqueConstraint(fields=["company", "rfq", "supplier"], name="uniq_supplier_quote_per_rfq_company")]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.rfq_id and self.status == "submitted" and self.rfq.status != "open":
            raise ValidationError({"rfq": "Supplier quotations can only be submitted while the RFQ is open."})
        if self.rfq_id and self.supplier_id and self.rfq.company_id and self.supplier.company_id != self.rfq.company_id:
            raise ValidationError("The supplier and RFQ must belong to the same company.")
        if self.supplier_id and not self.supplier.is_active:
            raise ValidationError({"supplier": "Choose an active supplier."})
        if self.quoted_unit_price is not None and self.quoted_unit_price <= 0:
            raise ValidationError({"quoted_unit_price": "Enter a price greater than zero."})

    def save(self, *args, **kwargs):
        self._fill_company()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total(self):
        return (Decimal(self.rfq.quantity) * Decimal(self.quoted_unit_price)).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.rfq.number} - {self.supplier.name}"


class GoodsReceipt(CompanyOwned):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="receipts")
    receipt_date = models.DateField(default=timezone.localdate)
    quantity_received = models.PositiveIntegerField(default=1)
    delivery_note = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-receipt_date", "-id"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.purchase_order_id:
            return
        if self.quantity_received is None or self.quantity_received < 1:
            raise ValidationError({"quantity_received": "Received quantity must be at least one."})
        received = GoodsReceipt.objects.filter(purchase_order_id=self.purchase_order_id).exclude(pk=self.pk).aggregate(total=models.Sum("quantity_received"))["total"] or 0
        if received + self.quantity_received > self.purchase_order.quantity:
            raise ValidationError({"quantity_received": f"This would exceed the purchase order quantity ({self.purchase_order.quantity - received} remaining)."})
        if self.purchase_order.status in ("draft", "cancelled"):
            raise ValidationError("Goods can only be received against an ordered purchase order.")

    def save(self, *args, **kwargs):
        self._fill_company()
        self.full_clean()
        super().save(*args, **kwargs)
        received = GoodsReceipt.objects.filter(purchase_order=self.purchase_order).aggregate(total=models.Sum("quantity_received"))["total"] or 0
        if received >= self.purchase_order.quantity:
            PurchaseOrder.objects.filter(pk=self.purchase_order_id).update(status="received")

    def delete(self, *args, **kwargs):
        po_id = self.purchase_order_id
        super().delete(*args, **kwargs)
        remaining = GoodsReceipt.objects.filter(purchase_order_id=po_id).aggregate(total=models.Sum("quantity_received"))["total"] or 0
        po = PurchaseOrder.objects.filter(pk=po_id).first()
        if po and po.status == "received" and remaining < po.quantity:
            PurchaseOrder.objects.filter(pk=po_id).update(status="ordered")

    def __str__(self):
        return f"Receipt for {self.purchase_order.number}"


class RequisitionAuthority(models.Model):
    """Department-scoped permissions explicitly delegated by that department's HOD or company admin."""
    company = models.ForeignKey("accounts.Company", on_delete=models.CASCADE, related_name="requisition_authorities")
    department = models.ForeignKey("accounts.Module", on_delete=models.CASCADE, related_name="requisition_authorities")
    membership = models.ForeignKey("accounts.Membership", on_delete=models.CASCADE, related_name="requisition_authorities")
    can_initiate = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    granted_by = models.ForeignKey("accounts.Membership", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="granted_requisition_authorities")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department__label", "membership__user__last_name", "membership__user__first_name"]
        constraints = [models.UniqueConstraint(fields=["company", "department", "membership"],
                                               name="uniq_req_authority_company_dept_member")]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.membership_id and self.company_id and self.membership.company_id != self.company_id:
            raise ValidationError("The assigned user must belong to the same company.")
        if self.department_id and self.company_id and not self.company.modules.filter(pk=self.department_id).exists():
            raise ValidationError("Choose a department enabled for this company.")
        if self.membership_id and self.department_id and not self.membership.modules.filter(pk=self.department_id).exists() and self.membership.role != "admin":
            raise ValidationError("The assigned user must belong to the selected department.")
        if not self.can_initiate and not self.can_approve:
            raise ValidationError("Select at least one delegated permission.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.membership} — {self.department.label}"
