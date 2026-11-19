# Verified ERP ↔ POS shop linking

This package adds a signed owner-approval flow. ERP company administrators can request a shop link, but the mapping is not activated until the registered POS shop owner signs in to POS and approves it. The owner's POS password is never requested by ERP.

## Important settings

Set these environment variables in **both** Django processes:

- `POS_LINK_SHARED_SECRET`: one long random secret, exactly the same in ERP and POS. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and copy the same value into both process environments. Never commit the real value to source control.
- `ERP_PUBLIC_BASE_URL`: the ERP URL reachable from the browser that will approve the POS request. For a same-computer local test, `http://127.0.0.1:8000`; on a LAN, use the ERP computer's reachable LAN URL instead. This must match in both processes.
- `POS_PUBLIC_BASE_URL`: the POS URL reachable from the browser, e.g. `http://172.18.6.25:8000` for the current local setup.

On Windows PowerShell, set the variables **in each terminal before starting that app**:

```powershell
$env:POS_LINK_SHARED_SECRET = "PASTE_THE_SAME_LONG_RANDOM_SECRET_HERE"
$env:ERP_PUBLIC_BASE_URL = "http://127.0.0.1:8000"
$env:POS_PUBLIC_BASE_URL = "http://172.18.6.25:8000"
```

Use a LAN-reachable ERP URL instead of `127.0.0.1` if the approving browser is on another computer. `127.0.0.1` always means the computer running the browser.

## Apply migrations

### POS project

Activate the POS project's own virtual environment and run migrations against the same `posApp` SQL Server database used by POS:

```powershell
python manage.py migrate posApp
```

This creates `ERPShopLinkRequest` and `ERPShopLinkAudit` tables. They keep pending/decided request records and the POS-side audit history.

### ERP project

Activate the ERP project's virtual environment and run:

```powershell
python manage.py migrate pos_bridge
```

This creates the ERP request/audit tables and enforces one active assignment per POS shop with a unique shop ID. If your existing ERP database already contains duplicate mappings for the same POS shop, resolve those duplicates before applying the migration.

## Owner approval flow

1. A company administrator opens **POS Intelligence → Shop & branch links**.
2. They select a shop and optional branch scope and submit the request.
3. The browser redirects to the POS authorization page. If needed, the POS owner signs in.
4. POS checks that the authenticated user is the registered owner (`Shop.owner.user_id`). Merely knowing a shop name or ID is not enough.
5. The owner approves or rejects the exact company/shop request. Requests expire after 20 minutes and can only be processed once.
6. POS records its decision and redirects to the ERP with a signed callback. ERP verifies the signature, request, expiry, company, and shop before activating the mapping.
7. ERP users see only the mappings for their active company. Every POS query remains filtered by that mapping. Revocations are audited.

## Notes and limitations

- The initial implementation blocks reassigning a shop that is already linked to another ERP company. It does not implement transfers or shared access. Those need a separate explicit workflow with owner authorization and a documented access policy.
- This integration is read-only for POS operational records.
- Use HTTPS, a strong secret, and a reachable public/LAN hostname in production. Rotate any credentials that were previously stored in source files.
- The POS table search/pagination control displays 10 or 15 rows at a time and searches rows rendered on the current page. The ERP POS data lists use database-side search and pagination (10 or 15 records per page).


`\.env.example` is a reference template only; these current settings read operating-system environment variables and do not automatically load that file. In PowerShell, set the variables in each terminal before launching `python manage.py runserver`, or configure them in Windows Environment Variables.
