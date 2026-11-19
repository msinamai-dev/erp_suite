# Multi-company workspace and branding update

This update changes the ERP foundation so one user account can belong to more than one approved company and switch between those workspaces after signing in.

## Included
- Memberships now allow one user to belong to multiple companies, while preventing duplicate memberships for the same user/company pair.
- A session-based company switcher appears in the top bar when the user belongs to more than one approved company.
- Company profile now supports business type, tagline, logo URL, primary/accent colours, currency code, and a JSON configuration field for future company-specific settings.
- Sidebar branding and main action colours use the active company's colours.
- Existing enabled-module selection continues to determine which ERP modules are available to each company.
- Team management can link an existing username to another company without resetting that user's password.
- Company context remains isolated when switching workspaces; the current employee/leave summary is scoped to the active company.

## Apply the update
1. Back up the project and database.
2. Merge the files from this archive into your existing project.
3. Activate your existing virtual environment.
4. Run:

   ```powershell
   python manage.py migrate
   python manage.py check
   python manage.py runserver
   ```

5. Sign in as a company administrator and open **Administration → Company profile** to set the business type, logo, colours, currency and enabled modules.
6. To link an existing user to another company, use that company's **Team & access → Add team member** and enter the existing username. Leave the password blank and use the email already associated with the account.

## Important limitations
- This is the multi-company, access and branding foundation. Industry-specific integrations such as live GPS telemetry still require external services and additional implementation.
- `logo_url` accepts a URL; use a trusted HTTPS image URL. Local file uploads need a separate media-storage setup.
- Test on a database backup before production. The current execution environment did not have Django installed, so `manage.py check` and migrations could not be run here; Python syntax compilation passed.


### Company logo uploads
Company admins can upload a logo image from Company Profile. Install the added Pillow dependency, run migrations, and configure `MEDIA_ROOT`/`MEDIA_URL` for development. In production, serve uploaded media through your web server or object storage; do not use Django development media serving in production.

## Added industry workflows

The project includes optional company modules. The tobacco module has been removed; Finance & Accounting and E-Procurement have been expanded in this release. A company administrator can enable the modules needed for that company in Company Profile; the available module catalogue is seeded by migration `accounts.0004_seed_erp_modules`.

### Transport & Logistics (`/transport/`)
- Driver register and licence expiry dates.
- Fleet register with capacity, odometer, insurance and service dates.
- Trips/consignments with driver, vehicle, origin, destination, planned/actual timing, cargo and status.
- Delivery updates with timestamp, location, optional GPS coordinates and status note.
- Fuel, service, repair, toll and other vehicle expenses.

### Retail & Wholesale (`/retail/`)
- Retail/wholesale sale records with customer, product, quantity, payment method, discount and total.
- Completing a sale reduces the product's stock and blocks completion when stock is insufficient.
- Stock receipt, sale/dispatch, return and adjustment movements update stock quantities.
- Existing Sales customers, products, pricing and sales orders remain available.

All new business records inherit the company-scoped data model. Enable only the modules relevant to each company and assign module access to each staff membership. New database migrations must be applied after updating the code.

### Important implementation notes
- These are operational foundations. The new finance reports are based on general-ledger entries and require correct account setup; e-procurement is not yet a public supplier portal or a full three-way invoice-matching system.
- The current POS sale model records one product per sale. A full basket checkout, barcode scanner, receipt printing, live map feed and automated posting to the general ledger would be separate enhancements.
- Stock movements update quantities when saved; use a return or adjustment to correct stock history rather than deleting records that have already affected stock.
- Test the new modules in a copy of the database before production. This environment does not have Django installed, so only Python syntax compilation was available here; run `python manage.py check` and `python manage.py migrate` in your project environment before use.
