# Meridian ERP (Django + SQL Server)

One configurable, multi-company system for **Sales, HR, Finance & Accounting, E-Procurement, IT, Estates, Construction, Transport & Logistics, and Retail & Wholesale**.

| Module | Screens |
|---|---|
| Sales | Customers, Products, Sales orders |
| HR | Employees, Departments, Leave requests, Payroll |
| Finance & Accounting | Invoices, payments, expenses, chart of accounts, journal, trial balance, P&L, balance sheet, receivables ageing |
| E-Procurement | Suppliers, requisition approvals, RFQs, supplier quotes, purchase orders, goods receipts |
| IT | Assets, Support tickets, Software licences |
| Estates | Properties, Units, Leases, Maintenance |
| Construction | Projects, Tasks, Subcontracts (project spend comes from Accounting expenses) |

The home dashboard shows revenue, receivables, active projects, headcount, open tickets, unit occupancy, a sales chart and a "needs attention" list. Finance has its own receivables and reporting workspace; E-Procurement supports requisition-to-order workflow and receiving.

## Quick start (Windows)

1. Install **Python 3.12+** and the **ODBC Driver 17 (or 18) for SQL Server**.
2. In SSMS create an empty database: `CREATE DATABASE ErpDB;`
3. Open `setup.bat`, adjust `DB_HOST` / `DB_USER` / `DB_PASSWORD` / `DB_DRIVER` if needed
   (leave `DB_USER` empty to use Windows authentication; use `DB_DRIVER=ODBC Driver 18 for SQL Server` for driver 18).
4. Double-click `setup.bat`. It creates a virtual environment, installs packages, builds the tables,
   loads demo data and starts the server.
5. Open http://127.0.0.1:8000 and sign in with `admin` / `admin123`. **Change this password** (Admin site > Users).

Next time just run `run.bat`.

### Manual commands

```
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo          # optional demo data
python manage.py createsuperuser    # if you skipped the demo data
python manage.py runserver
```

### Trying it without SQL Server
Set `DB_ENGINE=sqlite` before running the commands above. The code is identical; only the database changes.

## Settings you will likely change
* `ERP_COMPANY` (env var) - company name in the sidebar and login page. `ERP_CURRENCY` - currency symbol.
* `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS` before going live.

## How it is built
* `core/` - dashboard, layout, and `crud.py`, a helper that gives each model list / search / create / edit / delete screens.
* Each module is its own app (`sales`, `hr`, `accounting`, `procurement`, `it_ops`, `estates`, `construction`).
  Adding a standard register = add a model, then one `crud_urls(...)` line in that app's `urls.py` and an entry in `core/navigation.py`. Workflow screens can add dedicated views and status transitions.
* Reference numbers (SO-00001, INV-00001, EMP-00001 ...) and totals are generated automatically.
* Every model is also available in Django's `/admin/`.

## Known limits of this first version
* Sales and purchase orders hold one product/item line each (no multi-line orders yet).
* The page fonts, Bootstrap, icons and Chart.js load from CDNs, so the browser needs internet access.

## Companies, departments and users
* **Register a company** at `/register/` (link on the sign-in page): company details, the departments it wants
  (Sales, HR, Accounting, ...), and the first administrator.
* New companies are **locked until approved**. The system owner (a superuser such as `admin`) approves them under
  *Registered companies* in the sidebar. Set `ERP_AUTO_APPROVE_COMPANIES=1` to approve automatically.
* A company administrator uses *Team & access* to add each person and tick **one or several departments** for them,
  and *Company profile* to change the company's departments. Admins can use every department the company has.
* Users only see (and can only open) their departments, including on the dashboard. Superusers see everything.
* After pulling this update, run `python manage.py migrate` to apply the included migrations. If you modify models locally, run `python manage.py makemigrations` before migrating. Use `python manage.py setup_company_chart COMPANY_ID` to seed a starter chart of accounts for an existing company.

## Each company sees only its own data
* Every business record (customers, invoices, employees, projects, ...) belongs to one company. Company users only ever
  see, search, edit or delete their own company's records, including dashboard figures, reports and dropdown lists.
* Codes that must be unique (account codes, product SKUs, HR department names) are unique **per company**, so two
  companies can both have account `1000`.
* The system owner (superuser) is not restricted and sees every company's data in one place.
* Data created before this update has no company. Give it to one company with
  `python manage.py assign_company "Company name"`; until then only superusers can see it.
* `python manage.py seed_demo` now creates a demo company with all the sample data (sign in as `demo` / `demo123`).

## HR: status, leave and payroll
* **Status** (Active / On leave / Terminated) is changed in one click from an employee's profile (eye icon in the
  Employees list). Only *Active* people appear in "assigned to", "project manager" and "requested by" lists.
  *Terminated* people are left off new payroll and their sign-in is switched off (reinstating them switches it back on).
* **Payroll:** every new employee is added to the current month's payroll automatically. *Generate month* on the
  Payroll screen adds everyone for any other month.
* **Leave:** each employee earns 3 working days a month (edit `LEAVE` in `settings.py`), unused days carry over and
  approved leave is deducted. Employees linked to a sign-in see *My leave* in the sidebar to check their balance and
  request leave; HR approves or rejects from the Leave requests list. Link existing people via the "Sign-in account"
  field on the employee form. After pulling this update run `makemigrations hr construction it_ops procurement` + `migrate`.
