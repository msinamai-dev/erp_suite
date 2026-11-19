# Added RFQs, supplier quotations and goods receipts for the e-procurement workflow.
import django.utils.timezone
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_company_logo_upload'),
        ('procurement', '0003_alter_requisition_requested_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequestForQuotation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(blank=True, editable=False, max_length=20, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('item', models.CharField(max_length=200)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('closing_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('open', 'Open for quotes'), ('closed', 'Closed'), ('awarded', 'Awarded')], default='draft', max_length=10)),
                ('notes', models.TextField(blank=True)),
                ('company', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='accounts.company')),
                ('requisition', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rfqs', to='procurement.requisition')),
            ],
            options={'ordering': ['-id']},
        ),
        migrations.CreateModel(
            name='SupplierQuote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quoted_unit_price', models.DecimalField(decimal_places=2, max_digits=14)),
                ('lead_time_days', models.PositiveIntegerField(default=0)),
                ('valid_until', models.DateField(blank=True, null=True)),
                ('terms', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('selected', 'Selected'), ('rejected', 'Not selected')], default='submitted', max_length=10)),
                ('submitted_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('company', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='accounts.company')),
                ('rfq', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quotes', to='procurement.requestforquotation')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='quotes', to='procurement.supplier')),
            ],
            options={'ordering': ['quoted_unit_price', 'lead_time_days']},
        ),
        migrations.CreateModel(
            name='GoodsReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receipt_date', models.DateField(default=django.utils.timezone.localdate)),
                ('quantity_received', models.PositiveIntegerField(default=1)),
                ('delivery_note', models.CharField(blank=True, max_length=100)),
                ('notes', models.TextField(blank=True)),
                ('company', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='accounts.company')),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='receipts', to='procurement.purchaseorder')),
            ],
            options={'ordering': ['-receipt_date', '-id']},
        ),
        migrations.AddConstraint(
            model_name='supplierquote',
            constraint=models.UniqueConstraint(fields=('company', 'rfq', 'supplier'), name='uniq_supplier_quote_per_rfq_company'),
        ),
    ]
