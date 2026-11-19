import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_membership_position"),
        ("procurement", "0004_eprocurement_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="requisition",
            name="department",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="procurement_requisitions", to="accounts.module"),
        ),
        migrations.AddField(
            model_name="requisition",
            name="created_by",
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="created_requisitions", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="requisition",
            name="approved_by",
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="approved_requisitions", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="requisition",
            name="approved_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.CreateModel(
            name="RequisitionAuthority",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("can_initiate", models.BooleanField(default=False)),
                ("can_approve", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name="requisition_authorities", to="accounts.company")),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name="requisition_authorities", to="accounts.module")),
                ("granted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                 related_name="granted_requisition_authorities", to="accounts.membership")),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name="requisition_authorities", to="accounts.membership")),
            ],
            options={"ordering": ["department__label", "membership__user__last_name", "membership__user__first_name"]},
        ),
        migrations.AddConstraint(
            model_name="requisitionauthority",
            constraint=models.UniqueConstraint(fields=("company", "department", "membership"),
                                               name="uniq_req_authority_company_dept_member"),
        ),
    ]
