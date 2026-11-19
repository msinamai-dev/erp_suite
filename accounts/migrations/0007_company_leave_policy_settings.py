from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_company_frontend_tax_settings")]

    operations = [
        migrations.AddField(
            model_name="company",
            name="leave_days_per_month",
            field=models.PositiveSmallIntegerField(default=3, help_text="Working leave days accrued per month."),
        ),
        migrations.AddField(
            model_name="company",
            name="leave_deduct_types",
            field=models.JSONField(blank=True, default=list, help_text="Leave types that consume the accrued leave balance."),
        ),
    ]
