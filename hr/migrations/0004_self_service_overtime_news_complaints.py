import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0003_employee_leave_start_employee_user"),
        ("accounts", "0005_remove_tobacco_business_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="payroll", name="overtime", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payroll", name="bonus", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.CreateModel(
            name="OvertimeEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="accounts.company")),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("hours", models.DecimalField(decimal_places=2, max_digits=7)),
                ("hourly_rate", models.DecimalField(decimal_places=2, default=0, help_text="Rate per hour; set by HR according to company policy.", max_digits=14)),
                ("reason", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("paid", "Paid")], default="pending", max_length=10)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="overtime_entries", to="hr.employee")),
            ],
            options={"ordering": ["-date", "employee__first_name"]},
        ),
        migrations.CreateModel(
            name="CompanyNews",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="accounts.company")),
                ("title", models.CharField(max_length=180)),
                ("body", models.TextField()),
                ("is_published", models.BooleanField(default=False)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("department", models.ForeignKey(blank=True, help_text="Leave blank to publish to the whole company.", null=True, on_delete=django.db.models.deletion.SET_NULL, to="hr.department")),
            ],
            options={"ordering": ["-published_at", "-id"], "verbose_name": "company news item", "verbose_name_plural": "company news"},
        ),
        migrations.CreateModel(
            name="EmployeeComplaint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="accounts.company")),
                ("number", models.CharField(blank=True, max_length=20, unique=True)),
                ("anonymous", models.BooleanField(default=True)),
                ("category", models.CharField(choices=[("workplace", "Workplace concern"), ("safety", "Health and safety"), ("harassment", "Harassment or bullying"), ("payroll", "Pay or benefits"), ("management", "Management concern"), ("other", "Other")], default="other", max_length=20)),
                ("subject", models.CharField(max_length=180)),
                ("description", models.TextField()),
                ("status", models.CharField(choices=[("new", "New"), ("reviewing", "Under review"), ("resolved", "Resolved"), ("closed", "Closed")], default="new", max_length=12)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("resolution_notes", models.TextField(blank=True)),
                ("employee", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="complaints", to="hr.employee")),
            ],
            options={"ordering": ["-submitted_at", "-id"], "verbose_name": "employee complaint"},
        ),
    ]
