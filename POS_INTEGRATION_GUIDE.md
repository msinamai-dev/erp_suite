# POS data integration

The ERP includes a read-only POS Intelligence area. It reads the separate POS database using the `pos` database alias; it does not merge databases, write to POS tables, or duplicate records into ERP.

## Displayed data
- Dashboard: sales today and over the last seven days, transaction count, product count, low stock, recent receipts, top-selling products.
- Product catalogue: POS code, category, unit, cost, selling price, stock and active status.
- Sales transactions: date filters, receipt code, customer, branch, payment method, subtotal, tax and total.
- Receipt detail: individual product lines, quantities, prices and line totals.
- POS purchase orders, stock history, expenses and till shifts.

## Database settings
The ERP's normal database remains `DATABASES["default"]` (ErpDB). The separate POS database is configured through:
- `POS_DB_NAME` (default `posApp`)
- `POS_DB_HOST` and `POS_DB_PORT` (fall back to `DB_HOST` and `DB_PORT`)
- `POS_DB_USER` and `POS_DB_PASSWORD` (fall back to `DB_USER` and `DB_PASSWORD`)
- `POS_DB_DRIVER` (falls back to `DB_DRIVER`, then ODBC Driver 17 for SQL Server)
- `POS_DB_EXTRA_PARAMS` (defaults to `TrustServerCertificate=yes;`)

If both databases are on the same SQL Server instance and use the same login, only `POS_DB_NAME=posApp` may be needed. Otherwise set the POS-specific host/instance and credentials. Use a SQL login with read-only permissions for the POS tables used by this feature. If no username is set, Windows authentication is used.

## Setup
1. Back up the ERP project and both databases.
2. Copy the updated project files while preserving local environment variables and secrets.
3. Make sure the POS database is reachable from the ERP host.
4. Run `python manage.py migrate`, then `python manage.py check`, then `python manage.py runserver`.
5. As company admin, open **POS Intelligence → Shop & branch links** and map the POS shop and optionally a branch to the ERP company. A blank branch means all branches for that shop.
6. Give staff access to the ERP Retail or Sales module; POS Intelligence is read-only.

## Scope and safeguards
- Each ERP company sees only its own configured shop/branch links.
- Staff must have Retail or Sales access.
- POS screens are read-only. Removing a mapping never deletes POS data.
- Tables are expected to be named `posApp_shop`, `posApp_branch`, `posApp_products`, `posApp_transaction`, `posApp_salesitem`, `posApp_purchaseorder`, `posApp_stockhistory`, `posApp_expense`, `posApp_shift`, and `posApp_category`.

## Accounting recommendation
Treat POS sales as source reports first. Do not automatically post each transaction to the ERP ledger until cash/bank/EcoCash, revenue, VAT, returns, discounts, COGS and stock-account mappings are defined and reconciled. A later controlled journal/import workflow should use duplicate prevention and audit trails.

## Security note
The supplied POS source has credentials and payment/email configuration hardcoded in its settings. Move those secrets to environment variables and rotate any credentials that have been shared or used outside a trusted local environment before production use.
