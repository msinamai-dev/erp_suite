# Finance & E-Procurement update

## Changes
- Removed the Tobacco Operations module from navigation, URL registration, installed apps and source code.
- Removed the tobacco company-type option; existing companies using that value are migrated to `general`.
- Fixed sidebar link generation to respect a tile's explicit namespace. This fixes Retail links that point to Sales records.
- Reworked Finance & Accounting into a finance workspace with receivables, overdue balances, receipts, expenses, invoices, trial balance, P&L, balance sheet and receivables ageing.
- Added a starter company chart of accounts command: `python manage.py setup_company_chart COMPANY_ID`.
- Expanded Procurement into E-Procurement with requisition approvals, RFQs, supplier quotes, quote award to a draft purchase order, purchase order issue/cancel actions and goods receipts including partial receipts.
- Updated demo data and setup documentation.

## Apply to an existing checkout
1. Back up the database and project folder.
2. Replace the project code with this version (or merge the changed files).
3. Activate the existing virtual environment.
4. Run `python manage.py migrate`.
5. Run `python manage.py check`.
6. Restart the server.
7. For each company that needs a starter ledger, run `python manage.py setup_company_chart COMPANY_ID` using that company's numeric ID.

## Notes
- The tobacco application source and URL registration are removed. To avoid destructive data loss, existing tobacco database tables are not dropped automatically; they are orphaned and unused by this code release.
- Finance reports are based on journal entries. Check chart-of-account mappings and opening balances before relying on the reports for formal/statutory accounting.
- E-Procurement is an internal workflow foundation, not yet a public supplier portal, electronic tender platform, or full three-way invoice matching implementation.
- The package was statically compiled, but Django runtime checks and browser tests could not be run in this build environment because Django is not installed here. Run the listed checks in your project virtual environment before using it operationally.
