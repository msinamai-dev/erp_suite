from django import forms
from django.core.exceptions import ValidationError

from accounts.access import get_membership
from accounts.models import Membership, Module
from .access import managed_departments
from .models import RequisitionAuthority


class RequisitionAuthorityForm(forms.ModelForm):
    class Meta:
        model = RequisitionAuthority
        fields = ["department", "membership", "can_initiate", "can_approve"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        current = get_membership(user)
        departments = managed_departments(user)
        self.fields["department"].queryset = Module.objects.filter(pk__in=[d.pk for d in departments])
        self.fields["membership"].queryset = Membership.objects.none()
        self.fields["department"].widget.attrs["class"] = "form-select"
        self.fields["membership"].widget.attrs["class"] = "form-select"
        for field in ("can_initiate", "can_approve"):
            self.fields[field].widget.attrs["class"] = "form-check-input"
        dept_id = self.data.get("department") or self.initial.get("department")
        if dept_id and current:
            self.fields["membership"].queryset = Membership.objects.filter(
                company=current.company, role="member", user__is_active=True, modules__pk=dept_id
            ).select_related("user").distinct().order_by("user__first_name", "user__last_name", "user__username")
        self.fields["department"].label = "Department"
        self.fields["membership"].label = "Staff member in this department"

    def clean(self):
        data = super().clean()
        if not data.get("can_initiate") and not data.get("can_approve"):
            raise ValidationError("Select at least one permission to delegate.")
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        actor = get_membership(self.user)
        obj.company = actor.company
        obj.granted_by = actor
        if commit:
            obj.save()
        return obj
