from django.db import migrations

MODULES = [
    ("sales", "Sales", "bi-bag-check", "#2F6F8F", "Customers, products and sales orders.", 10),
    ("hr", "Human Resources", "bi-person-badge", "#B4533C", "Staff, leave and payroll.", 20),
    ("accounting", "Accounting", "bi-calculator", "#3E7C59", "Invoices, payments, expenses and reports.", 30),
    ("procurement", "Procurement", "bi-truck", "#A17A1F", "Suppliers, requisitions and purchase orders.", 40),
    ("it_ops", "IT", "bi-pc-display", "#5B6B7A", "IT assets, licences and support tickets.", 50),
    ("estates", "Estates", "bi-buildings", "#7C5C3E", "Properties, leases and maintenance.", 60),
    ("construction", "Construction", "bi-cone-striped", "#D9822B", "Projects, tasks and subcontractors.", 70),
    ("tobacco", "Tobacco Operations", "bi-flower1", "#8B6B3F", "Growers, crop intake, weighing, grading and settlements.", 80),
    ("transport", "Transport & Logistics", "bi-truck", "#326B8C", "Fleet, drivers, trips and delivery tracking.", 90),
    ("retail", "Retail & Wholesale", "bi-shop", "#4B7554", "Retail sales, wholesale orders and stock movements.", 100),
]

def seed_modules(apps, schema_editor):
    Module = apps.get_model("accounts", "Module")
    for key, label, icon, color, blurb, sort in MODULES:
        Module.objects.update_or_create(key=key, defaults={"label": label, "icon": icon, "color": color, "blurb": blurb, "sort": sort})

def unseed_modules(apps, schema_editor):
    Module = apps.get_model("accounts", "Module")
    Module.objects.filter(key__in=["tobacco", "transport", "retail"]).delete()

class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_company_logo_upload")]
    operations = [migrations.RunPython(seed_modules, unseed_modules)]
