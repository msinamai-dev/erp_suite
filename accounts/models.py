from django.conf import settings
from django.db import models


class Module(models.Model):
    """A department a company can switch on: one per ERP module (Sales, HR, Accounting ...)."""

    key = models.CharField(max_length=30, unique=True)
    label = models.CharField(max_length=60)
    icon = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=9, blank=True)
    blurb = models.CharField(max_length=200, blank=True)
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort", "label"]
        verbose_name = "department"

    def __str__(self):
        return self.label


class Company(models.Model):
    BUSINESS_TYPES = [
        ("general", "General business"),
        ("transport", "Transport and logistics"),
        ("retail", "Retail / wholesale"),
        ("services", "Service provider"),
        ("mixed", "Goods and services"),
    ]

    name = models.CharField(max_length=150, unique=True)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, default="general")
    tagline = models.CharField(max_length=160, blank=True)
    logo = models.ImageField(upload_to="company_logos/", blank=True, help_text="Upload a PNG, JPG, or WebP company logo.")
    # Kept for backward compatibility with any previously configured external logo URLs.
    logo_url = models.URLField(blank=True, help_text="Legacy logo URL; use the uploaded logo field instead.")
    primary_color = models.CharField(max_length=7, default="#245A49", help_text="Hex colour, e.g. #245A49")
    accent_color = models.CharField(max_length=7, default="#D8A33E", help_text="Hex colour, e.g. #D8A33E")
    currency_code = models.CharField(max_length=3, default="USD")
    configuration = models.JSONField(default=dict, blank=True, help_text="Additional company-specific feature settings.")
    registration_number = models.CharField(max_length=60, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    postal_address = models.TextField(blank=True)
    vat_registered = models.BooleanField(default=False, help_text="Enable VAT calculations and tax invoice labels for this company.")
    vat_number = models.CharField(max_length=60, blank=True, help_text="VAT registration number entered by the company administrator.")
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=15, help_text="Company-configured VAT percentage. Set to 0 when no VAT applies.")
    currency_name = models.CharField(max_length=40, default="dollars", help_text="Currency name used when writing invoice amounts in words.")
    bank_details = models.TextField(blank=True, help_text="Bank/payment instructions printed on invoices.")
    invoice_terms = models.TextField(blank=True, default="Payment is due by the due date shown. Please quote the invoice number as your payment reference.", help_text="Default payment terms printed on invoices.")
    leave_days_per_month = models.PositiveSmallIntegerField(default=3, help_text="Working leave days accrued per month.")
    leave_deduct_types = models.JSONField(default=list, blank=True, help_text="Leave types that consume the accrued leave balance.")
    modules = models.ManyToManyField(Module, related_name="companies", verbose_name="departments")
    is_approved = models.BooleanField(default=False, help_text="Companies can only use the system once approved.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class Membership(models.Model):
    """Links one user to one company, with a role and the departments they may use."""

    ROLES = [("admin", "Company admin"), ("member", "Staff member")]
    POSITIONS = [
        ("staff", "Staff member"),
        ("hod", "Head of Department (HOD)"),
        ("procurement_officer", "Procurement officer"),
        ("procurement_manager", "Procurement manager"),
        ("finance_officer", "Finance / accounts officer"),
        ("hr_officer", "Human resources officer"),
        ("executive", "Executive / senior management"),
        ("it_officer", "IT officer"),
        ("custom", "Other / custom position"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="members")
    role = models.CharField(max_length=10, choices=ROLES, default="member")
    job_title = models.CharField(max_length=100, blank=True, help_text="Optional detailed job title.")
    position = models.CharField(max_length=30, choices=POSITIONS, default="staff", db_index=True)
    modules = models.ManyToManyField(Module, blank=True, related_name="memberships", verbose_name="departments",
                                     help_text="Ignored for company admins, who can use every department the company has.")

    class Meta:
        ordering = ["user__first_name", "user__username"]
        constraints = [models.UniqueConstraint(fields=["user", "company"], name="unique_user_company_membership")]

    def __str__(self):
        return f"{self.user} @ {self.company}"
