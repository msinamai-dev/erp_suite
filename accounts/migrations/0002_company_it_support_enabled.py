from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="company",
            name="it_support_enabled",
            field=models.BooleanField(default=True, help_text="Allow employees to raise IT support tickets for this company."),
        ),
    ]
