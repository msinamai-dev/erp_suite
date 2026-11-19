import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0002_company_it_support_enabled"),
        ("hr", "0003_employee_leave_start_employee_user"),
        ("it_ops", "0003_alter_asset_assigned_to_alter_ticket_requested_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="department",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="support_tickets", to="hr.department"),
        ),
        migrations.CreateModel(
            name="TicketComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="accounts.company")),
                ("message", models.TextField()),
                ("is_internal", models.BooleanField(default=False, help_text="Internal notes are visible only to authorized IT staff.")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("ticket", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="it_ops.ticket")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]
