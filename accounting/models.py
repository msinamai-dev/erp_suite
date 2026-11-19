from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from core.models import CompanyOwned, Numbered, money


class Account(CompanyOwned):
    TYPES = [("asset", "Asset"), ("liability", "Liability"), ("equity", "Equity"),
             ("revenue", "Revenue"), ("expense", "Expense")]

    code = models.CharField(max_length=10)
    name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=10, choices=TYPES)
    description = models.CharField(max_length=250, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="uniq_account_code_per_company")]

    def __str__(self):
        return f"{self.code} - {self.name}"


class JournalEntry(CompanyOwned):
    date = models.DateField(default=timezone.localdate)
    reference = models.CharField(max_length=40, blank=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="entries")
    description = models.CharField(max_length=250)
    debit = money(default=0)
    credit = money(default=0)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "journal entry"
        verbose_name_plural = "journal entries"

    def __str__(self):
        return f"{self.date} {self.account.code}"


def _accounting_setting(key):
    defaults = {"AUTOPOST": True, "CASH": "1000", "RECEIVABLE": "1100", "REVENUE": "4000"}
    return {**defaults, **getattr(settings, "ACCOUNTING", {})}[key]


def clear_journal(company_id, reference):
    """Remove the auto-posted entries for one document (by its reference number)."""
    if _accounting_setting("AUTOPOST") and reference:
        JournalEntry._base_manager.filter(company_id=company_id, reference=reference).delete()


def post_journal(company_id, reference, date, description, debit_key, credit_key, amount):
    """Post (or re-post) one balanced entry pair for a document, keyed by its reference number.

    Idempotent: entries already carrying this reference are replaced, so editing an invoice or
    payment never double-counts. Uses the document's own company chart of accounts, and is skipped
    quietly when auto-posting is off or the configured account codes don't exist for that company.
    """
    if not _accounting_setting("AUTOPOST") or not reference:
        return
    clear_journal(company_id, reference)
    if not amount or amount <= 0:
        return
    accounts = Account._base_manager.filter(company_id=company_id)
    dr = accounts.filter(code=_accounting_setting(debit_key)).first()
    cr = accounts.filter(code=_accounting_setting(credit_key)).first()
    if not (dr and cr):
        return
    JournalEntry.objects.create(company_id=company_id, date=date, reference=reference, account=dr,
                                description=description, debit=amount)
    JournalEntry.objects.create(company_id=company_id, date=date, reference=reference, account=cr,
                                description=description, credit=amount)


class Invoice(Numbered):
    PREFIX = "INV"
    STATUS = [("draft", "Draft"), ("sent", "Sent"), ("paid", "Paid"),
              ("overdue", "Overdue"), ("cancelled", "Cancelled")]

    customer = models.ForeignKey("sales.Customer", on_delete=models.PROTECT)
    sales_order = models.ForeignKey("sales.SalesOrder", on_delete=models.SET_NULL, null=True, blank=True)
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    amount = money()
    amount_paid = money(default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    notes = models.TextField(blank=True, default="",
                             help_text="Printed on the invoice (delivery details, project reference, etc.).")

    class Meta:
        ordering = ["-issue_date", "-id"]

    @property
    def balance(self):
        return self.amount - self.amount_paid

    @property
    def days_overdue(self):
        if self.status in ("sent", "overdue") and self.balance > 0 and self.due_date < timezone.localdate():
            return (timezone.localdate() - self.due_date).days
        return 0

    def computed_status(self):
        """Status implied by payments and due date. Draft and cancelled are never changed automatically."""
        if self.status in ("draft", "cancelled"):
            return self.status
        if self.amount > 0 and self.amount_paid >= self.amount:
            return "paid"
        return "overdue" if self.due_date < timezone.localdate() else "sent"

    @classmethod
    def refresh_overdue(cls):
        """Keep sent/overdue/paid statuses in step with due dates and payments (cheap bulk updates)."""
        today = timezone.localdate()
        cls.objects.filter(status__in=["sent", "overdue"], amount__gt=0,
                           amount_paid__gte=F("amount")).update(status="paid")
        cls.objects.filter(status="sent", due_date__lt=today).update(status="overdue")
        cls.objects.filter(status="overdue", due_date__gte=today).update(status="sent")

    def apply_payment_delta(self, delta):
        """Add/remove money from amount_paid atomically, then move the status accordingly."""
        with transaction.atomic():
            if delta:
                Invoice._base_manager.filter(pk=self.pk).update(amount_paid=F("amount_paid") + delta)
            fresh = Invoice._base_manager.get(pk=self.pk)
            new_status = fresh.computed_status()
            if new_status != fresh.status:
                Invoice._base_manager.filter(pk=self.pk).update(status=new_status)
        self.refresh_from_db(fields=["amount_paid", "status"])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep the general ledger in step: Dr Accounts receivable / Cr Sales revenue once issued.
        if self.status in ("draft", "cancelled"):
            clear_journal(self.company_id, self.number)
        else:
            post_journal(self.company_id, self.number, self.issue_date, f"Invoice {self.number}",
                         "RECEIVABLE", "REVENUE", self.amount)

    def __str__(self):
        return self.number or "New invoice"


class Payment(Numbered):
    """A receipt against an invoice. Saving or deleting one keeps the invoice and the ledger in step."""

    PREFIX = "RCT"
    METHODS = [("cash", "Cash"), ("bank", "Bank transfer"), ("mobile", "Mobile money"),
               ("card", "Card / POS"), ("cheque", "Cheque")]

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    date = models.DateField(default=timezone.localdate)
    amount = money()
    method = models.CharField(max_length=10, choices=METHODS, default="bank")
    reference = models.CharField(max_length=60, blank=True,
                                 help_text="Bank reference, cheque number or mobile-money transaction ID.")

    class Meta:
        ordering = ["-date", "-id"]

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Enter an amount greater than zero."})
        if self.invoice_id:
            if self.invoice.status in ("draft", "cancelled"):
                raise ValidationError(f"This invoice is {self.invoice.get_status_display().lower()}. "
                                      "Mark it as sent before recording payments.")
            if self.amount:
                allowed = self.invoice.balance
                if self.pk:
                    allowed += (Payment.objects.filter(pk=self.pk, invoice_id=self.invoice_id)
                                .values_list("amount", flat=True).first() or Decimal("0"))
                if self.amount > allowed:
                    raise ValidationError({"amount": f"More than the outstanding balance ({allowed:,.2f})."})

    @transaction.atomic
    def save(self, *args, **kwargs):
        old = Payment.objects.filter(pk=self.pk).values("invoice_id", "amount").first() if self.pk else None
        super().save(*args, **kwargs)
        if old and old["invoice_id"] != self.invoice_id:  # payment moved to another invoice
            Invoice._base_manager.get(pk=old["invoice_id"]).apply_payment_delta(-old["amount"])
            old = None
        self.invoice.apply_payment_delta(self.amount - (old["amount"] if old else Decimal("0")))
        post_journal(self.company_id, self.number, self.date, f"Receipt {self.number} for {self.invoice.number}",
                     "CASH", "RECEIVABLE", self.amount)

    def __str__(self):
        return self.number or "New payment"


class Expense(CompanyOwned):
    CATEGORIES = [("materials", "Materials"), ("labour", "Labour"), ("plant", "Plant & fuel"),
                  ("utilities", "Utilities"), ("travel", "Travel"), ("office", "Office"), ("other", "Other")]
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("paid", "Paid"), ("rejected", "Rejected")]

    date = models.DateField(default=timezone.localdate)
    category = models.CharField(max_length=12, choices=CATEGORIES, default="other")
    description = models.CharField(max_length=250)
    paid_to = models.CharField(max_length=150, blank=True)
    amount = money()
    project = models.ForeignKey("construction.Project", on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="expenses", help_text="Charge this cost to a project (optional).")
    status = models.CharField(max_length=10, choices=STATUS, default="pending")

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return self.description


@receiver(post_delete, sender=Payment)
def _payment_deleted(sender, instance, **kwargs):
    invoice = Invoice._base_manager.filter(pk=instance.invoice_id).first()
    if invoice:
        invoice.apply_payment_delta(-instance.amount)
    clear_journal(instance.company_id, instance.number)


@receiver(post_delete, sender=Invoice)
def _invoice_deleted(sender, instance, **kwargs):
    clear_journal(instance.company_id, instance.number)
