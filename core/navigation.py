"""Single source of truth for the sidebar, module home pages and dashboard links."""


def I(label, url, model=None, icon="bi-circle"):
    return {"label": label, "url": url, "model": model, "icon": icon}


MODULES = [
    {
        "key": "transport", "label": "Transport & Logistics", "icon": "bi-truck", "color": "#326B8C",
        "blurb": "Fleet, drivers, trip planning, delivery updates and operating costs.",
        "items": [
            I("Drivers", "driver_list", "transport.Driver", "bi-person-vcard"),
            I("Fleet", "vehicle_list", "transport.Vehicle", "bi-truck"),
            I("Trips and consignments", "trip_list", "transport.Trip", "bi-signpost-2"),
            I("Delivery tracking", "delivery-update_list", "transport.DeliveryUpdate", "bi-geo-alt"),
            I("Fleet expenses", "vehicle-expense_list", "transport.VehicleExpense", "bi-fuel-pump"),
        ],
    },
    {
        "key": "retail", "label": "Retail & Wholesale", "icon": "bi-shop", "color": "#4B7554",
        "blurb": "Retail and wholesale sales, stock receipts, dispatches and adjustments.",
        "items": [
            I("Sales and POS", "sale_list", "retail.RetailSale", "bi-receipt"),
            I("Stock movements", "stock-movement_list", "retail.StockMovement", "bi-boxes"),
            {**I("Products and prices", "product_list", "sales.Product", "bi-tags"), "namespace": "sales"},
            {**I("Customers", "customer_list", "sales.Customer", "bi-people"), "namespace": "sales"},
        ],
    },
    {
        "key": "pos_bridge", "label": "POS Intelligence", "icon": "bi-shop-window", "color": "#0F766E",
        "blurb": "Read-only products, sales, stock history, purchase records, expenses and till shifts from your separate POS database.",
        "items": [
            I("POS dashboard", "home", None, "bi-speedometer2"),
            I("Products & stock", "products", None, "bi-box-seam"),
            I("Sales transactions", "transactions", None, "bi-receipt"),
            I("POS purchase orders", "purchases", None, "bi-bag"),
            I("Stock history", "stock_history", None, "bi-arrow-left-right"),
            I("Expenses & shifts", "expenses", None, "bi-cash-stack"),
        ],
    },
    {
        "key": "sales", "label": "Sales", "icon": "bi-bag-check", "color": "#2F6F8F",
        "blurb": "Customers, products and customer orders.",
        "items": [
            {**I("Customers", "customer_list", "sales.Customer", "bi-people"), "namespace": "sales"},
            I("Products", "product_list", "sales.Product", "bi-box-seam"),
            I("Sales orders", "salesorder_list", "sales.SalesOrder", "bi-receipt"),
        ],
    },
    {
        "key": "hr", "label": "Human Resources", "icon": "bi-person-badge", "color": "#B4533C",
        "blurb": "Staff records, leave and monthly payroll.",
        "items": [
            I("Employees", "employee_list", "hr.Employee", "bi-person-vcard"),
            I("Departments", "department_list", "hr.Department", "bi-diagram-3"),
            I("Leave requests", "leave_list", "hr.LeaveRequest", "bi-calendar2-week"),
            I("Payroll", "payroll_list", "hr.Payroll", "bi-cash-stack"),
            I("Overtime", "overtime_list", "hr.OvertimeEntry", "bi-clock-history"),
            I("Company news", "news_list", "hr.CompanyNews", "bi-megaphone"),
            I("Complaints", "complaint_list", "hr.EmployeeComplaint", "bi-shield-exclamation"),
        ],
    },
    {
        "key": "accounting", "label": "Finance & Accounting", "icon": "bi-calculator", "color": "#256B58",
        "blurb": "General ledger, receivables, payments, expenses, journals and financial statements.",
        "items": [
            I("Invoices", "invoice_list", "accounting.Invoice", "bi-file-earmark-text"),
            I("Payments", "payment_list", "accounting.Payment", "bi-cash-coin"),
            I("Expenses", "expense_list", "accounting.Expense", "bi-wallet2"),
            I("Chart of accounts", "account_list", "accounting.Account", "bi-list-ol"),
            I("Journal", "journal_list", "accounting.JournalEntry", "bi-journal-text"),
            I("Trial balance", "trial_balance", None, "bi-bar-chart-steps"),
            I("Profit & loss", "profit_loss", None, "bi-graph-up-arrow"),
            I("Balance sheet", "balance_sheet", None, "bi-pie-chart"),
            I("Receivables ageing", "ageing_report", None, "bi-hourglass-split"),
        ],
    },
    {
        "key": "procurement", "label": "E-Procurement", "icon": "bi-bag-check", "color": "#A17A1F",
        "blurb": "Digital requisitions, approvals, supplier quotations, purchase orders and goods receiving.",
        "items": [
            I("Suppliers", "supplier_list", "procurement.Supplier", "bi-shop"),
            I("Requisitions", "requisition_list", "procurement.Requisition", "bi-clipboard-check"),
            I("Requests for quotation", "rfq_list", "procurement.RequestForQuotation", "bi-file-earmark-spreadsheet"),
            I("Supplier quotations", "supplierquote_list", "procurement.SupplierQuote", "bi-card-checklist"),
            I("Purchase orders", "purchaseorder_list", "procurement.PurchaseOrder", "bi-bag-plus"),
            I("Goods receipts", "goodsreceipt_list", "procurement.GoodsReceipt", "bi-box-seam"),
        ],
    },
    {
        "key": "it_ops", "label": "IT", "icon": "bi-pc-display", "color": "#5B6B7A",
        "blurb": "Hardware, software licences and the support desk.",
        "items": [
            I("Assets", "asset_list", "it_ops.Asset", "bi-laptop"),
            I("Support tickets", "ticket_list", "it_ops.Ticket", "bi-life-preserver"),
            I("Software licences", "license_list", "it_ops.SoftwareLicense", "bi-key"),
        ],
    },
    {
        "key": "estates", "label": "Estates", "icon": "bi-buildings", "color": "#7C5C3E",
        "blurb": "Property portfolio, units, leases and maintenance.",
        "items": [
            I("Properties", "property_list", "estates.Property", "bi-building"),
            I("Units", "unit_list", "estates.Unit", "bi-door-open"),
            I("Leases", "lease_list", "estates.Lease", "bi-file-earmark-ruled"),
            I("Maintenance", "maintenance_list", "estates.MaintenanceRequest", "bi-tools"),
        ],
    },
    {
        "key": "construction", "label": "Construction", "icon": "bi-cone-striped", "color": "#D9822B",
        "blurb": "Projects, site tasks and subcontractors.",
        "items": [
            I("Projects", "project_list", "construction.Project", "bi-kanban"),
            I("Tasks", "task_list", "construction.ProjectTask", "bi-check2-square"),
            I("Subcontracts", "subcontract_list", "construction.Subcontract", "bi-people-fill"),
        ],
    },
]
