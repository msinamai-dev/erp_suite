from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_modules(sender=None, **kwargs):
    """Make sure every ERP module in core/navigation.py exists as a selectable 'department'."""
    from django.db.utils import DatabaseError

    from core.navigation import MODULES

    from .models import Module

    try:
        for n, m in enumerate(MODULES):
            Module.objects.update_or_create(
                key=m["key"],
                defaults={"label": m["label"], "icon": m["icon"], "color": m["color"],
                          "blurb": m["blurb"], "sort": n},
            )
        # Remove the legacy module record so it cannot be assigned to companies or members.
        Module.objects.filter(key="tobacco").delete()
    except DatabaseError:  # tables not created yet (e.g. while running makemigrations)
        pass


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Companies & access"

    def ready(self):
        post_migrate.connect(sync_modules, sender=self)
