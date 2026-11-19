"""Settings for the Meridian ERP project (SQL Server by default)."""
import os
from pathlib import Path

from django.contrib.messages import constants as msg

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me-before-going-live")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---- Branding (shown in sidebar, login page and dashboard) -----------------
COMPANY_NAME = os.environ.get("ERP_COMPANY", "SINAMAI")
CURRENCY = os.environ.get("ERP_CURRENCY", "$")
# Company address, VAT registration, VAT rate, bank details and invoice terms are configured
# by each company administrator in the frontend Company profile screen.
#
ACCOUNTING = {"AUTOPOST": True, "CASH": "1000", "RECEIVABLE": "1100", "REVENUE": "4000"}

# New company registrations must be approved by the system owner (Registered companies page)
# before they can use anything. Set ERP_AUTO_APPROVE_COMPANIES=1 to approve automatically.
COMPANY_AUTO_APPROVE = os.environ.get("ERP_AUTO_APPROVE_COMPANIES", "0") == "1"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # ERP modules
    "core",
    "accounts",
    "sales",
    "transport",
    "retail",
    "hr",
    "accounting",
    "procurement",
    "it_ops",
    "estates",
    "construction",
    "pos_bridge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "accounts.middleware.CompanyAccessMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "erp_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context.erp",
            ],
        },
    },
]

WSGI_APPLICATION = "erp_project.wsgi.application"


POS_LINK_SHARED_SECRET = os.environ.get("J11nYGVqH83Pw_eaCgeyN-M0V9JeLMMDDgZEmIdGamnZzoSkbg7CM-DjGsQ7h0_j", "")

ERP_PUBLIC_BASE_URL = os.environ.get(
    "ERP_PUBLIC_BASE_URL",
    "http://127.0.0.1:8001"
).rstrip("/")

POS_PUBLIC_BASE_URL = os.environ.get(
    "POS_PUBLIC_BASE_URL",
    "http://127.0.0.1:8000"
).rstrip("/")


if os.environ.get("DB_ENGINE", "mssql").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    _user = os.environ.get("DB_USER", "")
    _extra = "TrustServerCertificate=yes;"
    if not _user:
        _extra += "Trusted_Connection=yes;"
    DATABASES = {
        "default": {
            "ENGINE": "mssql",
            "NAME": os.environ.get("DB_NAME", "ERPDB"),
            "HOST": os.environ.get("DB_HOST", "localhost\\SQLEXPRESS"),
            "PORT": os.environ.get("DB_PORT", ""),
            "USER": _user,
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "OPTIONS": {
                "driver": os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server"),
                "extra_params": _extra,
            },
        }
    }


# Separate POS database; the bridge models are unmanaged/read-only.
# Shop linking: set the same random POS_LINK_SHARED_SECRET in ERP and POS.
# Set ERP_PUBLIC_BASE_URL to an address reachable from the POS-owner browser, and POS_PUBLIC_BASE_URL to the POS URL.
_pos_user = os.environ.get("POS_DB_USER", os.environ.get("DB_USER", ""))
_pos_extra = os.environ.get("POS_DB_EXTRA_PARAMS", "TrustServerCertificate=yes;")
if not _pos_user:
    _pos_extra += "Trusted_Connection=yes;"
DATABASES["pos"] = {
    "ENGINE": "mssql",
    "NAME": os.environ.get("POS_DB_NAME", "posApp"),
    "HOST": os.environ.get("POS_DB_HOST", r"localhost\SQLEXPRESS"),
    "PORT": os.environ.get("POS_DB_PORT", os.environ.get("DB_PORT", "")),
    "USER": _pos_user,
    "PASSWORD": os.environ.get("POS_DB_PASSWORD", os.environ.get("DB_PASSWORD", "")),
    "OPTIONS": {
        "driver": os.environ.get("POS_DB_DRIVER", os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server")),
        "extra_params": _pos_extra,
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Harare"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

MESSAGE_TAGS = {msg.ERROR: "danger"}
