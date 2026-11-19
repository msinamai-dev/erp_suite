from django.contrib import admin

from .models import Company, Membership, Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "sort")


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    filter_horizontal = ("modules",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "is_approved", "created_at")
    list_filter = ("is_approved",)
    search_fields = ("name", "email")
    filter_horizontal = ("modules",)
    inlines = [MembershipInline]
    actions = ["approve", "suspend"]

    @admin.action(description="Approve selected companies")
    def approve(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="Suspend selected companies")
    def suspend(self, request, queryset):
        queryset.update(is_approved=False)
