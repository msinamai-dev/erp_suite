from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="company", name="business_type",
            field=models.CharField(choices=[("general", "General business"), ("tobacco", "Tobacco sales floor"), ("transport", "Transport and logistics"), ("retail", "Retail / wholesale"), ("services", "Service provider"), ("mixed", "Goods and services")], default="general", max_length=20),
        ),
        migrations.AddField(model_name="company", name="tagline", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="company", name="logo_url", field=models.URLField(blank=True, help_text="Optional HTTPS URL for your company logo.")),
        migrations.AddField(model_name="company", name="primary_color", field=models.CharField(default="#245A49", help_text="Hex colour, e.g. #245A49", max_length=7)),
        migrations.AddField(model_name="company", name="accent_color", field=models.CharField(default="#D8A33E", help_text="Hex colour, e.g. #D8A33E", max_length=7)),
        migrations.AddField(model_name="company", name="currency_code", field=models.CharField(default="USD", max_length=3)),
        migrations.AddField(model_name="company", name="configuration", field=models.JSONField(blank=True, default=dict, help_text="Additional company-specific feature settings.")),
        migrations.AlterField(
            model_name="membership", name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(fields=("user", "company"), name="unique_user_company_membership"),
        ),
    ]
