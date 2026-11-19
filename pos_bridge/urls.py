from django.urls import path
from . import views

app_name = "pos_bridge"
urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("transactions/", views.transactions, name="transactions"),
    path("transactions/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("purchases/", views.purchases, name="purchases"),
    path("stock-history/", views.stock_history, name="stock_history"),
    path("expenses/", views.expenses, name="expenses"),
    path("shop-links/", views.shop_links, name="shop_links"),
    path("owner-callback/", views.owner_callback, name="owner_callback"),
    path("shop-links/<int:pk>/delete/", views.delete_shop_link, name="delete_shop_link"),
]
