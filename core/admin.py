from django.apps import apps
from django.contrib import admin

for label in ("sales", "hr", "accounting", "procurement", "it_ops", "estates", "construction"):
    for model in apps.get_app_config(label).get_models():
        if not admin.site.is_registered(model):
            admin.site.register(model)
