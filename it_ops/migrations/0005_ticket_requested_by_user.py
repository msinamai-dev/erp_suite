import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("it_ops", "0004_ticket_department_ticketcomment"),
    ]
    operations = [
        migrations.AddField(
            model_name="ticket",
            name="requested_by_user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="support_tickets", to=settings.AUTH_USER_MODEL),
        ),
    ]
