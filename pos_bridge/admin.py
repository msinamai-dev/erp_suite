from django.contrib import admin
from .models import POSShopLink, POSLinkRequest, POSLinkAudit

@admin.register(POSShopLink)
class POSShopLinkAdmin(admin.ModelAdmin):
    list_display = ("company", "label", "shop_id", "branch_id", "active", "created_at")
    list_filter = ("company", "active")
    search_fields = ("company__name", "label")

@admin.register(POSLinkRequest)
class POSLinkRequestAdmin(admin.ModelAdmin):
    list_display = ("company", "shop_name", "shop_id", "status", "requested_by", "created_at", "expires_at", "approved_pos_user_id")
    list_filter = ("status", "created_at")
    search_fields = ("company__name", "shop_name", "requested_by__username")
    readonly_fields = tuple(field.name for field in POSLinkRequest._meta.fields)

@admin.register(POSLinkAudit)
class POSLinkAuditAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event", "company", "shop_id", "actor_label")
    list_filter = ("event", "created_at")
    search_fields = ("company__name", "actor_label", "event")
    readonly_fields = tuple(field.name for field in POSLinkAudit._meta.fields)
