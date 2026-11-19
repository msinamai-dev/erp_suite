from django.db import migrations, models


def normalise_legacy_business_type(apps, schema_editor):
    Company = apps.get_model('accounts', 'Company')
    Company.objects.filter(business_type='tobacco').update(business_type='general')


class Migration(migrations.Migration):
    dependencies = [('accounts', '0004_seed_erp_modules')]

    operations = [
        migrations.RunPython(normalise_legacy_business_type, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='company',
            name='business_type',
            field=models.CharField(choices=[('general', 'General business'), ('transport', 'Transport and logistics'), ('retail', 'Retail / wholesale'), ('services', 'Service provider'), ('mixed', 'Goods and services')], default='general', max_length=20),
        ),
    ]
