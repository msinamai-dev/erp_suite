from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Company, Membership, Module

User = get_user_model()
NEED_DEPARTMENT = "Choose at least one department."
LEAVE_TYPE_CHOICES = [("annual", "Annual"), ("sick", "Sick"), ("maternity", "Maternity / paternity"),
                      ("study", "Study"), ("unpaid", "Unpaid")]


def _style(form):
    for field in form.fields.values():
        w = field.widget
        if isinstance(w, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
            w.attrs["class"] = "form-check-input"
        elif isinstance(w, forms.SelectMultiple):
            continue  # departments are drawn by hand as cards
        elif isinstance(w, forms.Select):
            w.attrs["class"] = "form-select"
        else:
            w.attrs["class"] = "form-control"
        if isinstance(w, forms.Textarea):
            w.attrs["rows"] = 3


def _check_password(form, data, field="password"):
    pw = data.get(field)
    if not pw:
        return
    probe = User(username=data.get("username", ""), first_name=data.get("first_name", ""),
                 last_name=data.get("last_name", ""), email=data.get("email", ""))
    try:
        validate_password(pw, probe)
    except ValidationError as e:
        form.add_error(field, e)


def create_staff_record(company, user, job_title):
    """Give a sign-in account an HR employee record (so they appear on payroll and can request leave)."""
    from hr.models import Employee

    if Employee._base_manager.filter(user=user).exists():
        return None
    return Employee.objects.create(
        company=company, user=user, first_name=user.first_name or user.username, last_name=user.last_name,
        email=user.email, job_title=job_title, salary=0)


def sync_hr_departments(company, modules):
    """Create HR department records for newly enabled company modules without deleting custom departments."""
    from hr.models import Department

    for module in modules:
        Department.objects.get_or_create(company=company, name=module.label)


class CompanyRegistrationForm(forms.Form):
    # company
    company_name = forms.CharField(max_length=150, label="Company name")
    registration_number = forms.CharField(max_length=60, required=False, label="Registration / tax number")
    company_email = forms.EmailField(label="Company email")
    phone = forms.CharField(max_length=40, required=False)
    currency_code = forms.CharField(max_length=3, min_length=3, initial="USD", label="Currency code",
                                    help_text="Three-letter code such as USD, ZWL or ZAR.")
    address = forms.CharField(label="Physical / business address", widget=forms.Textarea,
                              help_text="Enter the address to appear on company documents.")
    postal_address = forms.CharField(required=False, widget=forms.Textarea, label="Postal address")
    vat_registered = forms.BooleanField(required=False, label="Company is VAT registered")
    vat_number = forms.CharField(max_length=60, required=False, label="VAT registration number")
    vat_rate = forms.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100,
                                  initial=15, label="VAT rate (%)")
    currency_name = forms.CharField(max_length=40, initial="dollars", label="Currency name")
    bank_details = forms.CharField(required=False, widget=forms.Textarea, label="Bank / payment details")
    invoice_terms = forms.CharField(required=False, widget=forms.Textarea, label="Default invoice payment terms")
    leave_days_per_month = forms.IntegerField(min_value=0, max_value=31, initial=3, label="Leave days accrued per month")
    leave_deduct_types = forms.MultipleChoiceField(choices=LEAVE_TYPE_CHOICES, required=False, initial=["annual"],
                                                    widget=forms.CheckboxSelectMultiple, label="Leave types that use this balance")
    # departments
    departments = forms.ModelMultipleChoiceField(
        queryset=Module.objects.all(), error_messages={"required": NEED_DEPARTMENT})
    # first administrator
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    email = forms.EmailField(label="Your email")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)

    def clean_currency_code(self):
        value = self.cleaned_data["currency_code"].strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValidationError("Use a three-letter currency code such as USD, ZWL or ZAR.")
        return value

    def clean_company_name(self):
        name = self.cleaned_data["company_name"].strip()
        if Company.objects.filter(name__iexact=name).exists():
            raise ValidationError("A company with this name is already registered.")
        return name

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is taken. Try another.")
        return username

    def clean(self):
        data = super().clean()
        if data.get("vat_registered") and not data.get("vat_number", "").strip():
            self.add_error("vat_number", "Enter the VAT registration number when VAT is enabled.")
        if data.get("vat_rate") is not None and not (0 <= data["vat_rate"] <= 100):
            self.add_error("vat_rate", "VAT rate must be between 0 and 100 percent.")
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "The two passwords don't match.")
            else:
                _check_password(self, data, "password1")
        return data

    @transaction.atomic
    def save(self, approved=False):
        d = self.cleaned_data
        company = Company.objects.create(
            name=d["company_name"], registration_number=d["registration_number"], email=d["company_email"],
            phone=d["phone"], currency_code=d["currency_code"].upper(), address=d["address"], postal_address=d["postal_address"],
            vat_registered=d["vat_registered"], vat_number=d["vat_number"], vat_rate=d["vat_rate"],
            currency_name=d["currency_name"], bank_details=d["bank_details"], invoice_terms=d["invoice_terms"],
            leave_days_per_month=d["leave_days_per_month"], leave_deduct_types=d["leave_deduct_types"],
            is_approved=approved)
        company.modules.set(d["departments"])
        sync_hr_departments(company, d["departments"])
        user = User.objects.create_user(
            username=d["username"], email=d["email"], password=d["password1"],
            first_name=d["first_name"], last_name=d["last_name"])
        Membership.objects.create(user=user, company=company, role="admin")
        if any(m.key == "hr" for m in d["departments"]):
            create_staff_record(company, user, job_title="Company administrator")
        return company, user


class CompanyForm(forms.ModelForm):
    modules = forms.ModelMultipleChoiceField(
        queryset=Module.objects.all(), label="Departments", error_messages={"required": NEED_DEPARTMENT})
    leave_deduct_types = forms.MultipleChoiceField(choices=LEAVE_TYPE_CHOICES, required=False,
                                                    widget=forms.CheckboxSelectMultiple,
                                                    label="Leave types that use this balance")

    class Meta:
        model = Company
        fields = ["name", "registration_number", "email", "phone", "address", "postal_address",
                  "business_type", "tagline", "logo", "primary_color", "accent_color", "currency_code",
                  "currency_name", "vat_registered", "vat_number", "vat_rate", "bank_details", "invoice_terms",
                  "leave_days_per_month", "leave_deduct_types", "modules"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address"].required = True
        self.fields["address"].label = "Physical / business address"
        self.fields["postal_address"].label = "Postal address"
        self.fields["vat_rate"].min_value = 0
        self.fields["vat_rate"].max_value = 100
        self.fields["logo"].widget.attrs.update({"accept": "image/png,image/jpeg,image/webp,image/gif"})
        self.fields["logo"].required = False
        self.fields["primary_color"].widget = forms.TextInput(attrs={"type": "color"})
        self.fields["accent_color"].widget = forms.TextInput(attrs={"type": "color"})
        self.fields["business_type"].widget.attrs["class"] = "form-select"
        if not self.is_bound and not self.instance.leave_deduct_types:
            self.initial["leave_deduct_types"] = ["annual"]
        _style(self)

    def save(self, commit=True):
        company = super().save(commit=commit)
        if commit:
            sync_hr_departments(company, self.cleaned_data["modules"])
        return company

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("vat_registered") and not cleaned.get("vat_number", "").strip():
            self.add_error("vat_number", "Enter the VAT registration number when VAT is enabled.")
        return cleaned

    def clean_currency_code(self):
        value = self.cleaned_data["currency_code"].strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValidationError("Use a three-letter currency code such as USD, ZWL or ZAR.")
        return value

    def clean_primary_color(self):
        value = self.cleaned_data["primary_color"]
        if len(value) != 7 or not value.startswith("#") or any(c not in "0123456789abcdefABCDEF" for c in value[1:]):
            raise ValidationError("Enter a valid hex colour such as #245A49.")
        return value

    def clean_accent_color(self):
        value = self.cleaned_data["accent_color"]
        if len(value) != 7 or not value.startswith("#") or any(c not in "0123456789abcdefABCDEF" for c in value[1:]):
            raise ValidationError("Enter a valid hex colour such as #D8A33E.")
        return value


class TeamUserForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    job_title = forms.CharField(max_length=100, required=False, label="Detailed job title")
    position = forms.ChoiceField(choices=[("", "Choose position / access level")] + Membership.POSITIONS, required=True,
                                 label="Position / access level",
                                 help_text="Choose the employee position. HODs can approve only for their assigned departments.")
    role = forms.ChoiceField(choices=Membership.ROLES, initial="member")
    departments = forms.ModelMultipleChoiceField(queryset=Module.objects.none(), required=False)
    is_active = forms.BooleanField(required=False, initial=True, label="Active (can sign in)")
    password = forms.CharField(widget=forms.PasswordInput(render_value=False), required=False)
    add_to_hr = forms.BooleanField(required=False, initial=True,
                                   label="Also add to the HR staff list (payroll and leave requests)")

    def __init__(self, *args, company, membership=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company, self.membership = company, membership
        self.fields["departments"].queryset = company.modules.all()
        # Offered when adding someone, if the company uses HR and they don't already have a staff record.
        if membership is not None or not company.modules.filter(key="hr").exists():
            del self.fields["add_to_hr"]
        if membership is None:
            self.fields["password"].required = False
            self.fields["password"].label = "Initial password (new account only)"
            self.fields["password"].help_text = "Leave blank to link an existing username; enter a password only for a new account."
        else:
            self.fields["password"].label = "New password"
            self.fields["password"].help_text = "Leave blank to keep the current password."
        _style(self)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        qs = User.objects.filter(username__iexact=username)
        if self.membership:
            qs = qs.exclude(pk=self.membership.user_id)
        if qs.exists() and Membership.objects.filter(user__username__iexact=username, company=self.company).exists():
            raise ValidationError("That user already belongs to this company.")
        return username

    def clean(self):
        d = super().clean()
        role = d.get("role")
        if role == "member" and not d.get("departments") and "departments" not in self.errors:
            self.add_error("departments", "Choose at least one department for a staff member.")
        if self.membership and self.membership.role == "admin" and (role != "admin" or not d.get("is_active")):
            others = (Membership.objects.filter(company=self.company, role="admin", user__is_active=True)
                      .exclude(pk=self.membership.pk).exists())
            if not others:
                raise ValidationError("A company needs at least one active administrator.")
        if not self.membership and d.get("username"):
            existing = User.objects.filter(username__iexact=d["username"]).first()
            if existing:
                if d.get("password"):
                    self.add_error("password", "Leave password blank when linking an existing account; this form must not reset another account's password.")
                if existing.email and d.get("email") and existing.email.lower() != d["email"].lower():
                    self.add_error("email", "For an existing account, use the email already registered to that account.")
                if Membership.objects.filter(user=existing, company=self.company).exists():
                    self.add_error("username", "That user already belongs to this company.")
            elif not d.get("password"):
                self.add_error("password", "Enter an initial password for a new account.")
        if d.get("password"):
            _check_password(self, d)
        return d

    @transaction.atomic
    def save(self):
        d = self.cleaned_data
        existing_user = User.objects.filter(username__iexact=d["username"]).first() if not self.membership else None
        user = self.membership.user if self.membership else (existing_user or User())
        is_new_user = user.pk is None
        if is_new_user or self.membership:
            user.username, user.email = d["username"], d["email"]
            user.first_name, user.last_name = d["first_name"], d["last_name"]
            user.is_active = d["is_active"]
        if d["password"]:
            user.set_password(d["password"])
        user.save()
        m = self.membership or Membership(user=user, company=self.company)
        m.role, m.job_title, m.position = d["role"], d["job_title"], d["position"]
        m.save()
        m.modules.set(d["departments"])
        if d.get("add_to_hr"):
            create_staff_record(self.company, user, job_title=d["job_title"] or "Staff member")
        self.password_changed = bool(d["password"])
        return m
