# ERP Industry Modules — Setup and First Use

## 1. Apply the update

Back up your database and project folder first. Extract the updated project, install the requirements in your virtual environment, then run:

```bash
python manage.py migrate
python manage.py check
python manage.py runserver
```

## 2. Enable modules for each company

Sign in as the company administrator, open Company Profile, and select the modules needed by that company. Transport and logistics companies can enable Transport & Logistics, Sales, Finance & Accounting, HR and E-Procurement. Retail/wholesale companies can enable Retail & Wholesale, Sales, Finance & Accounting and E-Procurement. Choose modules according to each business.

Then open Team Management and assign the appropriate modules to each staff member. Company administrators can access all modules enabled for their company.

## 3. Transport workflow

1. Register drivers and licence details.
2. Register vehicles and capacity, insurance and service dates.
3. Create a trip, select its vehicle and driver, and enter origin/destination, cargo and planned timings.
4. Add delivery updates as the consignment moves; GPS coordinates are optional fields.
5. Record fuel, maintenance, toll and other fleet expenses.

## 4. Retail/wholesale workflow

1. Maintain customers and products in the Sales module.
2. Record stock received using Stock Movements before selling stock that is not yet in the product's opening stock quantity.
3. Create a Retail/Wholesale Sale. Draft sales do not reduce stock; marking a sale Completed reduces stock and will be blocked if there is insufficient quantity.
4. Use returns or stock adjustments to correct inventory. Stock movement records update the stock balance.

## 5. Finance & accounting workflow

1. Create a company-specific chart of accounts. To load the starter chart, run `python manage.py setup_company_chart COMPANY_ID`.
2. Create customer invoices, mark issued invoices as sent, and record receipts against their outstanding balances.
3. Record expenses, maintain journal lines, and review the trial balance, profit & loss, balance sheet and receivables ageing.
4. Verify account mappings, opening balances, and journal entries before using reports for formal financial reporting.

## 6. E-procurement workflow

1. Register suppliers and raise internal requisitions.
2. Approve or reject pending requisitions from the E-Procurement dashboard.
3. Create an RFQ against an approved requisition, open it for quotes, then enter supplier quotations while the RFQ is open.
4. Close the RFQ and award the lowest submitted quotation. The system creates a draft purchase order for review.
5. Issue the purchase order, record goods receipts (partial receipts are supported), and monitor the PO until the ordered quantity is received.

## Current scope

The tobacco module has been removed from this release. E-Procurement provides a practical requisition-to-order workflow; it is not a supplier-facing public portal or a full three-way invoice-matching system. Financial statements use posted general-ledger entries; validate account mappings and opening balances before relying on reports for statutory filing.
