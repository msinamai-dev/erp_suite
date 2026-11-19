from django.urls import path, re_path

from core.crud import crud_urls

from . import views
from .models import GoodsReceipt, PurchaseOrder, Requisition, RequestForQuotation, Supplier, SupplierQuote

app_name = "procurement"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("delegations/", views.delegations, name="delegations"),
    re_path(r"^requisition/(?P<pk>\d+)/(?P<action>approve|reject)/$", views.requisition_action, name="requisition_action"),
    re_path(r"^purchaseorder/(?P<pk>\d+)/(?P<action>send|cancel)/$", views.order_action, name="order_action"),
    re_path(r"^rfq/(?P<pk>\d+)/(?P<action>open|close|award)/$", views.rfq_action, name="rfq_action"),
]
urlpatterns += crud_urls(Supplier, "supplier", ["name", "contact_person", "phone", "category", "rating", "is_active"],
                         "Suppliers", search=["name", "contact_person", "category"])
urlpatterns += crud_urls(Requisition, "requisition",
                         ["number", "department", "item", "quantity", "requested_by", "project", "needed_by", "status", "approved_by", "approved_at"],
                         "Requisitions", search=["number", "item", "project__name"])
urlpatterns += crud_urls(RequestForQuotation, "rfq",
                         ["number", "title", "requisition", "item", "quantity", "closing_date", "status"],
                         "Requests for quotation", search=["number", "title", "item"])
urlpatterns += crud_urls(SupplierQuote, "supplierquote",
                         ["rfq", "supplier", "quoted_unit_price", "lead_time_days", "valid_until", "status"],
                         "Supplier quotations", search=["rfq__number", "supplier__name"])
urlpatterns += crud_urls(PurchaseOrder, "purchaseorder",
                         ["number", "supplier", "item", "quantity", "total", "expected_date", "status"],
                         "Purchase orders", search=["number", "supplier__name", "item"])
urlpatterns += crud_urls(GoodsReceipt, "goodsreceipt",
                         ["purchase_order", "receipt_date", "quantity_received", "delivery_note"],
                         "Goods receipts", search=["purchase_order__number", "delivery_note"])
