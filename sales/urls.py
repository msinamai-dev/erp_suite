from django.urls import path

from core.crud import crud_urls, module_home

from .models import Customer, Product, SalesOrder

app_name = "sales"

urlpatterns = [path("", module_home, name="home")]
urlpatterns += crud_urls(Customer, "customer", ["name", "contact_person", "phone", "city", "is_active"],
                         "Customers", search=["name", "contact_person", "city", "email"])
urlpatterns += crud_urls(Product, "product", ["sku", "name", "category", "unit_price", "stock_qty", "is_active"],
                         "Products", search=["sku", "name", "category"])
urlpatterns += crud_urls(SalesOrder, "salesorder",
                         ["number", "customer", "product", "order_date", "quantity", "total", "status"],
                         "Sales orders", search=["number", "customer__name", "product__name"])
