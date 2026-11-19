from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_remove_tobacco_business_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="postal_address",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="company",
            name="vat_registered",
            field=models.BooleanField(default=False, help_text="Enable VAT calculations and tax invoice labels for this company."),
        ),
        migrations.AddField(
            model_name="company",
            name="vat_number",
            field=models.CharField(blank=True, help_text="VAT registration number entered by the company administrator.", max_length=60),
        ),
        migrations.AddField(
            model_name="company",
            name="vat_rate",
            field=models.DecimalField(decimal_places=2, default=15, help_text="Company-configured VAT percentage. Set to 0 when no VAT applies.", max_digits=5),
        ),
        migrations.AddField(
            model_name="company",
            name="currency_name",
            field=models.CharField(default="dollars", help_text="Currency name used when writing invoice amounts in words.", max_length=40),
        ),
        migrations.AddField(
            model_name="company",
            name="bank_details",
            field=models.TextField(blank=True, help_text="Bank/payment instructions printed on invoices."),
        ),
        migrations.AddField(
            model_name="company",
            name="invoice_terms",
            field=models.TextField(blank=True, default="Payment is due by the due date shown. Please quote the invoice number as your payment reference.", help_text="Default payment terms printed on invoices."),
        ),
    ]
