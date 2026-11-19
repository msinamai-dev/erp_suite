from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_legacy_it_support_default")]

    operations = [
        migrations.AddField(
            model_name="membership",
            name="position",
            field=models.CharField(
                choices=[
                    ("staff", "Staff member"),
                    ("hod", "Head of Department (HOD)"),
                    ("procurement_officer", "Procurement officer"),
                    ("procurement_manager", "Procurement manager"),
                    ("finance_officer", "Finance / accounts officer"),
                    ("hr_officer", "Human resources officer"),
                    ("executive", "Executive / senior management"),
                    ("it_officer", "IT officer"),
                    ("custom", "Other / custom position"),
                ],
                db_index=True,
                default="staff",
                max_length=30,
            ),
        ),
    ]
