# Frontend company configuration and HR self-service

## Company setup is managed in the ERP UI

Company administrators can use **Administration → Company profile** to configure the company's physical/business and postal addresses, registration details, phone and email, logo and branding, currency, VAT registration and VAT rate, bank/payment details, invoice terms, leave accrual rules, and enabled ERP modules. Company registration also collects the initial address, currency, VAT, payment and leave-policy values.

The invoice renderer reads address, VAT and payment details from the invoice's own company record. It no longer uses a hard-coded global address or global VAT rate. In this version invoice amounts are treated as VAT-inclusive; the company VAT rate controls the VAT breakdown printed on the invoice. Validate the applicable tax rate and tax registration requirements with the relevant tax authority before issuing tax invoices.

## HR features

- Employees with a linked employee record can request leave and see their balance and request history.
- Employees can log overtime. HR sets the hourly rate and approves it; approved hours feed into the corresponding pending payroll period.
- HR can enter bonuses, allowances and deductions on payroll lines. Net pay recalculates from basic pay + allowances + approved overtime + bonus − deductions.
- Payslips appear in the employee's self-service area after payroll is marked **Paid**.
- HR can create company-wide or department-specific news and publish it to employees.
- Employees can submit anonymous complaints. When anonymous is selected, the complaint model deliberately stores no employee link. The employee should keep the generated reference number.
- Selecting company modules during registration or later in Company profile creates missing HR department records from the selected module names. HR can also add custom departments through **HR → Departments**.

## Upgrade existing installation

Back up the database and project folder first. Copy the updated project files into your working project, preserving your local environment and secrets. From the project directory, activate the existing virtual environment and run:

```powershell
python manage.py migrate
python manage.py check
python manage.py runserver
```

The new migrations add company-level VAT/currency/address-related configuration, leave-policy settings, overtime, bonus, news and complaint storage. A compatibility migration also adds a default of `0` to the legacy SQL Server `it_support_enabled` column if that old column still exists without a default. It does not remove or rewrite that legacy column.

This project archive was statically checked for Python syntax. Run the migrations and Django checks against a backup of your actual SQL Server database before using it in production; the archive could not be integration-tested against your local database from this environment.

## Position-based access and requisition approvals

Company administrators manage staff positions under **Administration → Team & access**. When adding or editing a user, select a **Position / access level** and assign the departments the person belongs to. The key procurement positions are:

- **Head of Department (HOD):** can initiate requisitions for assigned departments and approve pending requisitions from those departments, but cannot approve their own request.
- **Procurement officer / Procurement manager:** can manage suppliers, RFQs, supplier quotations, purchase orders and goods receipts. This position does not automatically grant departmental requisition approval.
- **Staff member / other positions:** cannot initiate or approve requisitions unless authority is explicitly delegated.

An HOD opens **E-Procurement → Delegate access** and chooses a department and an active staff member assigned to that department. The HOD can grant **Initiate requisitions**, **Approve requisitions**, or both. Company administrators can manage delegations for any department in their company. Delegations are company- and department-scoped.

The server enforces these rules on the requisition create and approve endpoints, including direct URL requests. Requisition workflow states are changed through the workflow actions rather than editable status fields. Approval records the approver and approval time. The company must have the Procurement module enabled, and HOD/delegate accounts must be assigned to their relevant department.

After installing this update, run `python manage.py migrate`. Existing requisitions remain in the database; because older records have no department recorded, a company administrator or procurement staff member should edit each legacy requisition and assign its department before relying on HOD approval for it.
