import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

def company_field():
    return models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='accounts.company')

def number_field():
    return models.CharField(blank=True, editable=False, max_length=20, unique=True)

class Migration(migrations.Migration):
    initial = True
    dependencies = [('accounts', '0003_company_logo_upload'), ('sales', '0002_customer_company_product_company_salesorder_company_and_more')]
    operations = [
        migrations.CreateModel(name='StockMovement', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('company', company_field()), ('number', number_field()), ('movement_date', models.DateField(default=django.utils.timezone.localdate)), ('movement_type', models.CharField(choices=[('receipt', 'Stock received'), ('sale', 'Sale/dispatch'), ('return', 'Customer return'), ('adjustment_in', 'Positive adjustment'), ('adjustment_out', 'Negative adjustment')], max_length=16)), ('quantity', models.PositiveIntegerField()), ('reference', models.CharField(blank=True, max_length=100)), ('notes', models.TextField(blank=True)), ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='sales.product'))], options={'ordering': ['-movement_date', '-id']}),
        migrations.CreateModel(name='RetailSale', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('company', company_field()), ('number', number_field()), ('sale_date', models.DateTimeField(default=django.utils.timezone.now)), ('channel', models.CharField(choices=[('retail', 'Retail'), ('wholesale', 'Wholesale')], default='retail', max_length=12)), ('payment_method', models.CharField(choices=[('cash', 'Cash'), ('card', 'Card'), ('transfer', 'Bank transfer'), ('credit', 'Credit')], default='cash', max_length=20)), ('reference', models.CharField(blank=True, max_length=100)), ('quantity', models.PositiveIntegerField(default=1)), ('unit_price', models.DecimalField(decimal_places=2, default=0, max_digits=14)), ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)), ('total', models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=14)), ('status', models.CharField(choices=[('draft', 'Draft'), ('completed', 'Completed'), ('void', 'Voided')], default='draft', max_length=12)), ('stock_applied', models.BooleanField(default=False, editable=False)), ('notes', models.TextField(blank=True)), ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='sales.customer')), ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='sales.product'))], options={'ordering': ['-sale_date', '-id']}),
    ]
