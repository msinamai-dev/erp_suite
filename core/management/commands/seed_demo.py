"""Load realistic demo data so every screen has something to show.

Usage:  python manage.py seed_demo

Creates a demo company ("Meridian Group (demo)", all departments, already approved) that owns all of the
demo data, a company admin  demo / demo123, and the system-owner superuser  admin / admin123.
"""
import random
from datetime import timedelta
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.apps import sync_modules
from accounts.models import Company, Membership, Module
from core.tenancy import company_context
from accounting.models import Account, Expense, Invoice, JournalEntry, Payment
from construction.models import Project, ProjectTask, Subcontract
from estates.models import Lease, MaintenanceRequest, Property, Unit
from hr.models import Department, Employee, LeaveRequest, Payroll
from it_ops.models import Asset, SoftwareLicense, Ticket
from procurement.models import GoodsReceipt, PurchaseOrder, Requisition, RequestForQuotation, Supplier, SupplierQuote
from sales.models import Customer, Product, SalesOrder


class Command(BaseCommand):
    help = "Create demo data and an 'admin' user (password: admin123)."

    def handle(self, *args, **options):
        sync_modules()
        User = get_user_model()
        company, _ = Company.objects.get_or_create(
            name="Meridian Group (demo)",
            defaults={"email": "info@meridian.example.com", "phone": "+263 4 700 000",
                      "address": "14 Samora Machel Ave, Harare", "is_approved": True})
        company.modules.set(Module.objects.all())
        if not User.objects.filter(username="demo").exists():
            demo = User.objects.create_user("demo", "demo@example.com", "demo123", first_name="Demo", last_name="Admin")
            Membership.objects.create(user=demo, company=company, role="admin", job_title="Company administrator")
        with company_context(company.id):
            if Customer.objects.exists():
                self.stdout.write(self.style.WARNING("Data already present - skipping seed."))
                return
            self._load()
            demo = User.objects.get(username="demo")
            if not Employee.objects.filter(user=demo).exists():
                Employee.objects.create(first_name="Demo", last_name="Admin", job_title="Company administrator",
                                        salary=D("3000"), user=demo, email=demo.email)

    def _load(self):
        random.seed(7)
        today = timezone.localdate()
        d = lambda days: today + timedelta(days=days)

        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin123", first_name="Admin")

        # ---- HR
        depts = {n: Department.objects.create(name=n, head_name=h) for n, h in [
            ("Management", "T. Moyo"), ("Sales", "R. Dube"), ("Finance", "A. Chikore"), ("Human Resources", "P. Ncube"),
            ("Procurement", "K. Banda"), ("IT", "L. Sibanda"), ("Estates", "M. Phiri"), ("Projects & Site", "J. Mutasa")]}
        staff = [
            ("Tendai", "Moyo", "Managing Director", "Management", 6500), ("Rudo", "Dube", "Sales Manager", "Sales", 3200),
            ("Alex", "Chikore", "Finance Manager", "Finance", 3600), ("Patience", "Ncube", "HR Officer", "Human Resources", 2200),
            ("Kudzai", "Banda", "Procurement Officer", "Procurement", 2400), ("Lloyd", "Sibanda", "IT Administrator", "IT", 2800),
            ("Memory", "Phiri", "Estates Manager", "Estates", 3000), ("James", "Mutasa", "Senior Project Manager", "Projects & Site", 4200),
            ("Farai", "Chuma", "Site Engineer", "Projects & Site", 2900), ("Nyasha", "Gumbo", "Quantity Surveyor", "Projects & Site", 3100)]
        emps = []
        for i, (f, l, t, dept, sal) in enumerate(staff):
            emps.append(Employee.objects.create(first_name=f, last_name=l, job_title=t, department=depts[dept], salary=D(sal),
                                                email=f"{f.lower()}.{l.lower()}@example.com", phone=f"+263 77 {100 + i} {2000 + i * 7}",
                                                hire_date=d(-random.randint(200, 2500)), status="on_leave" if i == 3 else "active"))
        LeaveRequest.objects.create(employee=emps[3], leave_type="annual", start_date=d(-3), end_date=d(7), status="approved", reason="Family leave")
        LeaveRequest.objects.create(employee=emps[8], leave_type="sick", start_date=d(1), end_date=d(3), status="pending")
        LeaveRequest.objects.create(employee=emps[5], leave_type="study", start_date=d(14), end_date=d(18), status="pending", reason="Exam week")
        month_end = today.replace(day=1) - timedelta(days=1)
        for e in emps:
            Payroll.objects.create(employee=e, period=month_end, basic=e.salary, allowances=e.salary * D("0.08"),
                                   deductions=e.salary * D("0.11"), status="paid")

        # ---- Sales
        customers = [Customer.objects.create(name=n, contact_person=c, city=city, email=f"info@{n.split()[0].lower()}.example.com", phone="+263 4 700 100")
                     for n, c, city in [("Harare City Developments", "S. Marufu", "Harare"), ("Zambezi Roads Authority", "D. Tshuma", "Bulawayo"),
                                        ("Highveld Retail Group", "N. Mapfumo", "Harare"), ("Kopje Housing Trust", "E. Zulu", "Mutare"),
                                        ("Msasa Industrial Park", "G. Hove", "Harare"), ("Eastern Schools Board", "B. Chari", "Mutare")]]
        products = [Product.objects.create(sku=s, name=n, category=c, unit_price=D(p), stock_qty=q) for s, n, c, p, q in [
            ("CEM-50", "Cement 50kg bag", "Cement", "11.50", 1800), ("SND-M3", "River sand per m3", "Aggregates", "28.00", 400),
            ("BRK-FC", "Face common bricks (1000)", "Masonry", "95.00", 120), ("RBR-12", "Rebar 12mm x 12m", "Steel", "14.80", 900),
            ("RFS-IBR", "IBR roofing sheet 3m", "Roofing", "21.00", 650), ("PNT-20", "Exterior paint 20L", "Finishes", "74.00", 85),
            ("RMX-30", "Ready-mix concrete 30MPa per m3", "Concrete", "135.00", 200)]]
        orders = []
        for _ in range(18):
            p = random.choice(products)
            orders.append(SalesOrder.objects.create(
                customer=random.choice(customers), product=p, order_date=d(-random.randint(0, 165)),
                quantity=random.randint(5, 80), unit_price=p.unit_price, discount_pct=random.choice([0, 0, 5, 10]),
                status=random.choice(["confirmed", "delivered", "delivered", "draft", "cancelled"])))

        # ---- Accounting
        acc = {c: Account.objects.create(code=c, name=n, account_type=t) for c, n, t in [
            ("1000", "Cash at bank", "asset"), ("1100", "Accounts receivable", "asset"), ("1500", "Plant and equipment", "asset"),
            ("2000", "Accounts payable", "liability"), ("3000", "Owner's equity", "equity"), ("4000", "Sales revenue", "revenue"),
            ("5000", "Cost of materials", "expense"), ("5100", "Site labour", "expense"), ("6000", "Administration", "expense")]}

        def post(date_, ref, desc, dr, cr, amount):
            JournalEntry.objects.create(date=date_, reference=ref, account=acc[dr], description=desc, debit=amount)
            JournalEntry.objects.create(date=date_, reference=ref, account=acc[cr], description=desc, credit=amount)

        post(d(-170), "OPEN", "Owner capital introduced", "1000", "3000", D("250000"))
        post(d(-160), "PLT-01", "Excavator purchase", "1500", "1000", D("85000"))
        for so in orders:
            if so.status == "cancelled":
                continue
            status = random.choice(["paid", "paid", "sent", "overdue"]) if so.status == "delivered" else "sent"
            # Invoices and payments post their own ledger entries (Dr 1100 / Cr 4000, Dr 1000 / Cr 1100).
            inv = Invoice.objects.create(customer=so.customer, sales_order=so, issue_date=so.order_date,
                                         due_date=so.order_date + timedelta(days=30), amount=so.total,
                                         status="sent" if status == "paid" else status)
            if status == "paid":
                Payment.objects.create(invoice=inv, date=so.order_date + timedelta(days=12), amount=so.total,
                                       method=random.choice(["bank", "bank", "cash", "mobile", "cheque"]))

        # ---- Procurement
        suppliers = [Supplier.objects.create(name=n, contact_person=c, category=cat, rating=r, phone="+263 4 800 200", email=f"sales@{n.split()[0].lower()}.example.com")
                     for n, c, cat, r in [("Sable Cement Works", "O. Mlambo", "Cement", 4), ("Kariba Steel & Wire", "H. Nkomo", "Steel", 5),
                                          ("Limpopo Aggregates", "V. Sithole", "Aggregates", 3), ("Great Dyke Plant Hire", "C. Zimba", "Plant hire", 4)]]

        # ---- Construction
        clients = customers
        projects = []
        for name, client, site, mgr, budget, start, end, status, prog in [
            ("Msasa Warehouse Complex", clients[4], "Msasa, Harare", emps[7], 1850000, -140, 120, "in_progress", 58),
            ("Eastern Schools Block B", clients[5], "Chimanimani Rd, Mutare", emps[8], 620000, -60, 150, "in_progress", 27),
            ("Kopje Low-cost Housing, Phase 2", clients[3], "Sakubva, Mutare", emps[7], 940000, 10, 300, "planning", 0),
            ("Highveld Mall Refurbishment", clients[2], "Borrowdale, Harare", emps[9], 410000, -300, -20, "completed", 100)]:
            projects.append(Project.objects.create(name=name, client=client, site_location=site, manager=mgr, budget=D(budget),
                                                   start_date=d(start), end_date=d(end), status=status, progress=prog))
        for pr, tasks in [(projects[0], [("Site clearing & earthworks", "done", 100, -100), ("Foundations & slab", "done", 100, -50),
                                         ("Steel frame erection", "in_progress", 60, 25), ("Roofing", "todo", 0, 70), ("Electrical first fix", "todo", 0, 90)]),
                          (projects[1], [("Setting out", "done", 100, -45), ("Foundations", "in_progress", 55, 14), ("Brickwork to lintel", "blocked", 10, 30)])]:
            for n, st, pg, due in tasks:
                ProjectTask.objects.create(project=pr, name=n, status=st, progress=pg, due_date=d(due), assigned_to=random.choice(emps[7:]))
        Subcontract.objects.create(project=projects[0], contractor="Kwekwe Electrical Contractors", scope="Electrical installation", contract_value=D("185000"), status="active", start_date=d(-30))
        Subcontract.objects.create(project=projects[1], contractor="Dzivarasekwa Roofing", scope="Roof trusses and sheeting", contract_value=D("74000"), status="draft")
        for pr in projects[:2] + projects[3:]:
            for cat in ("materials", "labour", "plant"):
                amt = D(pr.budget) * D(random.choice(["0.06", "0.09", "0.12"])) * (D("1.0") if pr.progress else D("0.2"))
                Expense.objects.create(date=d(-random.randint(5, 90)), category=cat, description=f"{cat.title()} - {pr.name}",
                                       amount=amt.quantize(D("0.01")), project=pr, paid_to=random.choice(suppliers).name,
                                       status=random.choice(["approved", "paid", "paid"]))
        Expense.objects.create(description="Office stationery", category="office", amount=D("214.50"), status="pending")
        Expense.objects.create(description="Fuel for site vehicles", category="plant", amount=D("1380"), status="pending", project=projects[1])

        reqs = [Requisition.objects.create(item="Rebar 12mm x 12m", quantity=500, requested_by=emps[8], project=projects[0], needed_by=d(10), status="approved", justification="Slab pour next week"),
                Requisition.objects.create(item="Cement 50kg bag", quantity=2000, requested_by=emps[7], project=projects[1], needed_by=d(21), status="pending"),
                Requisition.objects.create(item="Scaffold hire (3 months)", quantity=1, requested_by=emps[8], project=projects[1], needed_by=d(30), status="pending")]
        PurchaseOrder.objects.create(supplier=suppliers[1], requisition=reqs[0], project=projects[0], item="Rebar 12mm x 12m", quantity=500, unit_cost=D("13.90"), expected_date=d(6), status="ordered")
        PurchaseOrder.objects.create(supplier=suppliers[0], project=projects[0], item="Cement 50kg bag", quantity=1200, unit_cost=D("10.80"), order_date=d(-20), expected_date=d(-12), status="received")
        PurchaseOrder.objects.create(supplier=suppliers[2], project=projects[1], item="River sand per m3", quantity=60, unit_cost=D("24.00"), status="draft")
        received_po = PurchaseOrder.objects.filter(status="received").first()
        if received_po:
            GoodsReceipt.objects.create(purchase_order=received_po, receipt_date=d(-12), quantity_received=received_po.quantity,
                                        delivery_note="DN-DEMO-001", notes="Demo receipt for a completed delivery")
        rfq = RequestForQuotation.objects.create(title="Steel reinforcement supply", requisition=reqs[0],
                                                  item="Rebar 12mm x 12m", quantity=500, closing_date=d(7), status="open")
        SupplierQuote.objects.create(rfq=rfq, supplier=suppliers[1], quoted_unit_price=D("13.90"), lead_time_days=6,
                                     valid_until=d(14), terms="Delivery to project site; payment per agreed terms")
        SupplierQuote.objects.create(rfq=rfq, supplier=suppliers[0], quoted_unit_price=D("14.25"), lead_time_days=4,
                                     valid_until=d(14), terms="Delivery included")

        # ---- IT
        for name, cat, who, st, cost in [("Dell Latitude 5440", "laptop", emps[2], "in_use", 1250), ("HP ProLiant ML350", "server", None, "in_use", 6800),
                                         ("Ubiquiti Dream Machine", "network", None, "in_use", 450), ("Lenovo ThinkPad T14", "laptop", emps[7], "in_use", 1420),
                                         ("Canon iR-ADV Printer", "printer", None, "repair", 3100), ("Spare laptop", "laptop", None, "in_stock", 980)]:
            Asset.objects.create(name=name, category=cat, assigned_to=who, status=st, cost=D(cost), purchase_date=d(-random.randint(60, 900)),
                                 warranty_expiry=d(random.randint(-60, 600)), serial_number=f"SN{random.randint(100000, 999999)}")
        for title, pri, st, who in [("Cannot connect to VPN from site office", "high", "open", emps[8]), ("Accounting software runs slowly", "medium", "in_progress", emps[2]),
                                    ("New starter laptop setup", "low", "open", emps[3]), ("Server disk space warning", "critical", "in_progress", None),
                                    ("Printer jams on level 2", "low", "resolved", emps[1])]:
            Ticket.objects.create(title=title, priority=pri, status=st, requested_by=who, assigned_to="Lloyd Sibanda")
        SoftwareLicense.objects.create(name="Microsoft 365 Business", vendor="Microsoft", seats=25, cost=D("3750"), expiry_date=d(200))
        SoftwareLicense.objects.create(name="AutoCAD", vendor="Autodesk", seats=4, cost=D("6400"), expiry_date=d(35))
        SoftwareLicense.objects.create(name="Sage Accounting", vendor="Sage", seats=6, cost=D("2100"), expiry_date=d(-10))

        # ---- Estates
        props = [Property.objects.create(name=n, property_type=t, address=a, city=c, value=D(v), status=s) for n, t, a, c, v, s in [
            ("Msasa Business Park", "commercial", "14 Mutare Rd, Msasa", "Harare", 2400000, "leased_out"),
            ("Borrowdale Court", "residential", "7 Sherwood Dr", "Harare", 1650000, "leased_out"),
            ("Chitungwiza Stand 4481", "land", "Seke Rd", "Chitungwiza", 180000, "development")]]
        units = []
        for pr, prefix, n, rent in [(props[0], "B", 4, 1800), (props[1], "A", 4, 650)]:
            for i in range(1, n + 1):
                units.append(Unit.objects.create(property=pr, unit_number=f"{prefix}{i}", floor=(i - 1) // 2, area_sqm=random.choice([60, 85, 120]), monthly_rent=D(rent), status="available"))
        for u, tenant, start, end in [(units[0], "Zimcare Pharmacies", -200, 160), (units[1], "Bright Accounting Services", -90, 40),
                                      (units[2], "Nova Logistics", -300, 25), (units[4], "R. and T. Mugabe", -30, 335), (units[5], "A. Katsande", -400, -10)]:
            Lease.objects.create(unit=u, tenant_name=tenant, start_date=d(start), end_date=d(end), monthly_rent=u.monthly_rent,
                                 deposit=u.monthly_rent, status="expired" if end < 0 else "active")
            u.status = "occupied" if end >= 0 else "available"
            u.save()
        units[3].status = "maintenance"; units[3].save()
        MaintenanceRequest.objects.create(property=props[0], unit=units[3], title="Roof leak above B4", priority="high", status="in_progress", cost=D("1200"))
        MaintenanceRequest.objects.create(property=props[1], title="Replace gate motor", priority="medium", status="open")
        MaintenanceRequest.objects.create(property=props[0], title="Repaint car park lines", priority="low", status="completed", cost=D("340"))

        self.stdout.write(self.style.SUCCESS("Demo data loaded for \"Meridian Group (demo)\". Sign in as demo / demo123 (company admin) or admin / admin123 (system owner). Change these passwords!"))
