from django.db import migrations


def remove_tobacco_module(apps, schema_editor):
    Module = apps.get_model("accounts", "Module")
    Module.objects.filter(key="tobacco").delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_company_leave_policy_settings")]

    operations = [migrations.RunPython(remove_tobacco_module, migrations.RunPython.noop)]
