from django.urls import path
from core.crud import crud_urls, module_home
from .models import StockMovement, RetailSale
app_name = "retail"
urlpatterns = [path("", module_home, name="home")]
urlpatterns += crud_urls(StockMovement, "stock-movement", ["number", "product", "movement_date", "movement_type", "quantity", "reference"], "Stock movements", search=["number", "product__name", "product__sku", "reference"])
urlpatterns += crud_urls(RetailSale, "sale", ["number", "sale_date", "channel", "customer", "product", "quantity", "total", "payment_method", "status"], "Retail and wholesale sales", search=["number", "customer__name", "product__name", "reference"])
