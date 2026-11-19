@echo off
REM One-shot setup for Windows. Run from the project folder.
REM Before running: create an empty database in SSMS (e.g. CREATE DATABASE ErpDB;)
REM and edit the DB_* values below if your server isn't plain "localhost".

set DB_NAME=ErpDB
set DB_HOST=localhost
set DB_USER=
set DB_PASSWORD=
set DB_DRIVER=ODBC Driver 17 for SQL Server

python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
echo.
echo Starting the server at http://127.0.0.1:8000  (login: admin / admin123)
python manage.py runserver
