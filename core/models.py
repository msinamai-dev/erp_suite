from django.db import models

from .tenancy import current_company_id


def money(**kw):
    """Standard money column."""
    kw.setdefault("max_digits", 14)
    kw.setdefault("decimal_places", 2)
    return models.DecimalField(**kw)


class CompanyScopedManager(models.Manager):
    """Default manager: inside a company's request only that company's rows are visible."""

    def get_queryset(self):
        qs = super().get_queryset()
        company_id = current_company_id()
        return qs.filter(company_id=company_id) if company_id else qs


class CompanyOwned(models.Model):
    """Abstract base for every business record. Each row belongs to exactly one company.

    * `objects` only returns the current company's rows (so lists, dashboards, reports, search and
      form dropdowns are all isolated without each view having to remember to filter).
    * `company` is filled in automatically when a record is saved.
    * Related-object access and cascades use the plain base manager, so they keep working.
    """

    company = models.ForeignKey("accounts.Company", null=True, blank=True, editable=False,
                                on_delete=models.PROTECT, related_name="+")

    objects = CompanyScopedManager()

    class Meta:
        abstract = True

    def _fill_company(self):
        if self.company_id is None:
            company_id = current_company_id()
            if company_id and company_id > 0:
                self.company_id = company_id

    def save(self, *args, **kwargs):
        self._fill_company()
        super().save(*args, **kwargs)

    # Forms exclude the (non-editable) company field, which would silently skip per-company
    # uniqueness checks. Put it back so "code/sku/name must be unique within a company" is enforced nicely.
    def validate_unique(self, exclude=None):
        self._fill_company()
        super().validate_unique([f for f in (exclude or []) if f != "company"])

    def validate_constraints(self, exclude=None):
        self._fill_company()
        super().validate_constraints([f for f in (exclude or []) if f != "company"])

    def unique_error_message(self, model_class, unique_check):
        if "company" in unique_check and len(unique_check) > 1:
            unique_check = tuple(f for f in unique_check if f != "company")
        return super().unique_error_message(model_class, unique_check)


class Numbered(CompanyOwned):
    """Abstract base that gives a record an auto reference such as SO-00012."""

    PREFIX = "DOC"
    number = models.CharField(max_length=20, unique=True, blank=True, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"{self.PREFIX}-{self.pk:05d}"
            type(self)._base_manager.filter(pk=self.pk).update(number=self.number)
