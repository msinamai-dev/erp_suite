from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("accounts.urls")),
    path("my/", include("hr.self_urls")),
    path("", include("core.urls")),
    path("sales/", include("sales.urls")),
    path("transport/", include("transport.urls")),
    path("retail/", include("retail.urls")),
    path("hr/", include("hr.urls")),
    path("accounting/", include("accounting.urls")),
    path("procurement/", include("procurement.urls")),
    path("it/", include("it_ops.urls")),
    path("estates/", include("estates.urls")),
    path("construction/", include("construction.urls")),
    path("pos-data/", include("pos_bridge.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
