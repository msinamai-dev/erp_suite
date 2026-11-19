from django.db import migrations


def ensure_legacy_column_default(apps, schema_editor):
    """Allow inserts on older SQL Server databases that retain a removed non-null column."""
    if schema_editor.connection.vendor != "microsoft":
        return
    sql = """
    IF OBJECT_ID(N'dbo.accounts_company', N'U') IS NOT NULL
       AND COL_LENGTH(N'dbo.accounts_company', N'it_support_enabled') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM sys.default_constraints dc
           INNER JOIN sys.columns c
               ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
           WHERE dc.parent_object_id = OBJECT_ID(N'dbo.accounts_company')
             AND c.name = N'it_support_enabled'
       )
    BEGIN
       ALTER TABLE dbo.accounts_company
       ADD CONSTRAINT DF_accounts_company_it_support_enabled DEFAULT (0) FOR it_support_enabled;
    END
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0008_remove_legacy_tobacco_module")]
    operations = [migrations.RunPython(ensure_legacy_column_default, migrations.RunPython.noop)]
