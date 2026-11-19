from django.db import migrations

def add_pos_bridge(apps, schema_editor):
    Module = apps.get_model("accounts", "Module")
    Company = apps.get_model("accounts", "Company")
    alias = schema_editor.connection.alias
    module, _ = Module.objects.using(alias).get_or_create(
        key="pos_bridge",
        defaults={"label": "POS Intelligence", "icon": "bi-shop-window", "color": "#0F766E",
                  "blurb": "Read-only POS products, sales, stock history and branch operations.", "sort": 35},
    )
    for company in Company.objects.using(alias).all():
        keys = set(company.modules.values_list("key", flat=True))
        if "retail" in keys or "sales" in keys:
            company.modules.add(module)

class Migration(migrations.Migration):
    dependencies = [("accounts", "0010_membership_position")]
    operations = [migrations.RunPython(add_pos_bridge, migrations.RunPython.noop)]
