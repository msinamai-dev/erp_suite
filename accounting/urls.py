from django.urls import path

from core.crud import crud_urls

from . import views
from .models import Account, Expense, Invoice, JournalEntry, Payment

app_name = "accounting"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("profit-loss/", views.profit_loss, name="profit_loss"),
    path("balance-sheet/", views.balance_sheet, name="balance_sheet"),
    path("trial-balance/", views.trial_balance, name="trial_balance"),
    path("ageing/", views.ageing_report, name="ageing_report"),
    # invoice extras (the list/create/edit/delete screens come from crud_urls below)
    path("invoice/export/csv/", views.invoice_export, name="invoice_export"),
    path("invoice/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoice/<int:pk>/print/", views.invoice_print, name="invoice_print"),
    path("invoice/<int:pk>/pay/", views.invoice_pay, name="invoice_pay"),
    path("invoice/<int:pk>/status/<str:status>/", views.invoice_set_status, name="invoice_status"),
]
urlpatterns += crud_urls(
    Invoice, "invoice",
    ["number", "customer", "issue_date", "due_date", "amount", "amount_paid", "balance", "status"],
    "Invoices", search=["number", "customer__name"],
    exclude=["amount_paid"],  # managed by Payments
    row_actions=[("invoice_detail", "bi-eye", "View invoice"),
                 ("invoice_print", "bi-printer", "Print invoice", True),
                 ("invoice_pay", "bi-cash-coin", "Record payment")],
    list_actions=[("invoice_export", "bi-download", "Export CSV")],
    before_list=Invoice.refresh_overdue,
)
urlpatterns += crud_urls(
    Payment, "payment", ["number", "date", "invoice", "amount", "method", "reference"],
    "Payments", search=["number", "invoice__number", "invoice__customer__name", "reference"],
)
urlpatterns += crud_urls(Expense, "expense",
                         ["date", "category", "description", "paid_to", "project", "amount", "status"],
                         "Expenses", search=["description", "paid_to", "project__name"])
urlpatterns += crud_urls(Account, "account", ["code", "name", "account_type", "is_active"],
                         "Chart of accounts", search=["code", "name"])
urlpatterns += crud_urls(JournalEntry, "journal",
                         ["date", "reference", "account", "description", "debit", "credit"],
                         "Journal", search=["reference", "description", "account__name", "account__code"])
