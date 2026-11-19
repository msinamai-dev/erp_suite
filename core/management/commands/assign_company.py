"""Give data created before companies existed to a company.

Usage:  python manage.py assign_company "Company name"

Records with no company are invisible to every company user (and only visible to superusers), so run this
once after upgrading if you already have data you want a company to keep.
"""
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Company
from core.models import CompanyOwned


class Command(BaseCommand):
    help = "Assign every record that has no company yet to the named company."

    def add_arguments(self, parser):
        parser.add_argument("company", help="Name of a registered company")

    def handle(self, *args, **options):
        company = Company.objects.filter(name__iexact=options["company"]).first()
        if company is None:
            names = ", ".join(Company.objects.values_list("name", flat=True)) or "none registered yet"
            raise CommandError(f"No company called '{options['company']}'. Registered companies: {names}")
        total = 0
        for model in apps.get_models():
            if issubclass(model, CompanyOwned):
                n = model._base_manager.filter(company__isnull=True).update(company=company)
                if n:
                    self.stdout.write(f"  {model._meta.label}: {n}")
                total += n
        self.stdout.write(self.style.SUCCESS(f"Assigned {total} record(s) to {company.name}."))
