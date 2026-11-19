from django import forms

from .models import EmployeeComplaint, LeaveRequest, OvertimeEntry, working_days


class MyLeaveForm(forms.Form):
    """Leave request an employee files for themselves."""

    leave_type = forms.ChoiceField(choices=LeaveRequest.TYPES, label="Type of leave",
                                   widget=forms.Select(attrs={"class": "form-select"}))
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"))
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}))

    def __init__(self, *args, employee, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee = employee

    def clean(self):
        d = super().clean()
        start, end, kind = d.get("start_date"), d.get("end_date"), d.get("leave_type")
        if not (start and end and kind):
            return d
        if end < start:
            self.add_error("end_date", "The end date can't be before the start date.")
            return d
        days = working_days(start, end)
        if days < 1:
            self.add_error("start_date", "That range only covers a weekend. Pick at least one working day.")
            return d
        clash = LeaveRequest.objects.filter(employee=self.employee, status__in=["pending", "approved"],
                                            start_date__lte=end, end_date__gte=start).exists()
        if clash:
            raise forms.ValidationError("You already have leave requested or approved on some of those dates.")
        if kind in {k for k, _ in LeaveRequest.TYPES} and LeaveRequest(leave_type=kind).uses_allowance:
            available = self.employee.leave_available
            if days > available:
                raise forms.ValidationError(
                    f"That's {days} working day{'s' if days != 1 else ''} but you only have {max(available, 0)} "
                    "available (days already requested are set aside).")
        d["days"] = days
        return d


class MyOvertimeForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"))
    hours = forms.DecimalField(min_value=0.25, max_value=24, max_digits=7, decimal_places=2,
                               widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.25"}))
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}))

    def clean_date(self):
        value = self.cleaned_data["date"]
        from django.utils import timezone
        if value > timezone.localdate():
            raise forms.ValidationError("Overtime can only be logged for today or an earlier date.")
        return value


class MyComplaintForm(forms.ModelForm):
    class Meta:
        model = EmployeeComplaint
        fields = ["anonymous", "category", "subject", "description"]
        widgets = {
            "anonymous": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["anonymous"].initial = True
        self.fields["anonymous"].label = "Submit anonymously"
        self.fields["anonymous"].help_text = "When selected, your employee identity is not saved with this complaint."
