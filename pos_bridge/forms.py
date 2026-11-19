from django import forms
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from .models import POSShop, POSBranch


class POSLinkRequestForm(forms.Form):
    shop_id = forms.ChoiceField(label="POS shop", choices=(), widget=forms.Select(attrs={"class": "form-select"}))
    branch_id = forms.ChoiceField(label="Branch scope (optional)", required=False, choices=(), widget=forms.Select(attrs={"class": "form-select"}), help_text="Leave blank to request access to the whole shop.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            shops = list(POSShop.objects.using("pos").filter(is_active=True).order_by("name"))
            self.fields["shop_id"].choices = [("", "Choose a POS shop…")] + [(str(s.pk), f"{s.name} — {s.location}") for s in shops]
            raw_shop_id = self.data.get(self.add_prefix("shop_id")) if self.is_bound else None
            branches = POSBranch.objects.using("pos").filter(is_active=True)
            branches = branches.filter(shop_id=int(raw_shop_id)) if raw_shop_id and str(raw_shop_id).isdigit() else branches.none()
            self.fields["branch_id"].choices = [("", "Whole shop / all branches")] + [(str(b.pk), f"{b.name} — {b.location}") for b in branches.order_by("name")]
        except DatabaseError:
            self.fields["shop_id"].choices = [("", "POS database unavailable")]
            self.fields["branch_id"].choices = [("", "POS database unavailable")]

    def clean(self):
        cleaned = super().clean()
        shop_id = cleaned.get("shop_id")
        branch_id = cleaned.get("branch_id")
        if not shop_id:
            return cleaned
        try:
            shop = POSShop.objects.using("pos").filter(pk=shop_id, is_active=True).first()
            if not shop:
                self.add_error("shop_id", "This POS shop is not active or could not be found.")
            elif branch_id and not POSBranch.objects.using("pos").filter(pk=branch_id, shop_id=shop.pk, is_active=True).exists():
                self.add_error("branch_id", "Choose an active branch belonging to the selected shop.")
        except DatabaseError as exc:
            raise ValidationError("The POS database is unavailable. Check the POS database connection.") from exc
        return cleaned
