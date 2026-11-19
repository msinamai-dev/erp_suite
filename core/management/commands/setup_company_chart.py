from django.core.management.base import BaseCommand, CommandError

from accounts.models import Company
from accounting.models import Account
from core.tenancy import company_context


DEFAULT_ACCOUNTS = [
    ("1000", "Cash at bank", "asset"), ("1010", "Cash on hand", "asset"),
    ("1100", "Accounts receivable", "asset"), ("1200", "Inventory", "asset"),
    ("1500", "Property, plant and equipment", "asset"),
    ("2000", "Accounts payable", "liability"), ("2100", "Tax payable", "liability"),
    ("2200", "Accrued expenses", "liability"), ("3000", "Owner's equity", "equity"),
    ("3100", "Retained earnings", "equity"), ("4000", "Sales revenue", "revenue"),
    ("4100", "Service revenue", "revenue"), ("5000", "Cost of sales", "expense"),
    ("5100", "Wages and salaries", "expense"), ("5200", "Rent and utilities", "expense"),
    ("5300", "Transport and fuel", "expense"), ("6000", "Office and administration", "expense"),
]


class Command(BaseCommand):
    help = "Create the standard starter chart of accounts for one company."

    def add_arguments(self, parser):
        parser.add_argument("company_id", type=int)

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(pk=options["company_id"])
        except Company.DoesNotExist as exc:
            raise CommandError("Company ID was not found.") from exc
        created = 0
        with company_context(company.pk):
            for code, name, kind in DEFAULT_ACCOUNTS:
                _, was_created = Account.objects.get_or_create(code=code, defaults={"name": name, "account_type": kind, "is_active": True})
                created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Chart of accounts ready for {company.name}; {created} accounts created."))
