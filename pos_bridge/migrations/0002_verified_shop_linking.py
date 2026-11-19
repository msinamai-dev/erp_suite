import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_pos_bridge_module"),
        ("pos_bridge", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="posshoplink",
            name="shop_id",
            field=models.PositiveIntegerField(unique=True, help_text="ID of the shop in the POS database. One ERP company per POS shop."),
        ),
        migrations.CreateModel(
            name="POSLinkRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("shop_id", models.PositiveIntegerField()),
                ("shop_name", models.CharField(max_length=255)),
                ("branch_id", models.PositiveIntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending owner approval"), ("approved", "Approved"), ("rejected", "Rejected"), ("expired", "Expired"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("approved_pos_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pos_link_requests", to="accounts.company")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pos_link_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="POSLinkAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("shop_id", models.PositiveIntegerField(blank=True, null=True)),
                ("event", models.CharField(max_length=50)),
                ("actor_label", models.CharField(blank=True, max_length=255)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="accounts.company")),
                ("request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to="pos_bridge.poslinkrequest")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
