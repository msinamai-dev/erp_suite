from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_multicompany_branding")]

    operations = [
        migrations.AddField(
            model_name="company",
            name="logo",
            field=models.ImageField(blank=True, help_text="Upload a PNG, JPG, or WebP company logo.", upload_to="company_logos/"),
        ),
    ]
