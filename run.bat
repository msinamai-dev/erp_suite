@echo off
REM Start the ERP again after the first setup.
set DB_NAME=ErpDB
set DB_HOST=localhost
set DB_USER=
set DB_PASSWORD=
set DB_DRIVER=ODBC Driver 17 for SQL Server
call venv\Scripts\activate
python manage.py runserver
