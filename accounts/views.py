from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .access import get_membership, user_memberships
from .apps import sync_modules
from .forms import CompanyForm, CompanyRegistrationForm, TeamUserForm
from .models import Company, Membership, Module


def _modules():
    if not Module.objects.exists():
        sync_modules()
    return Module.objects.all()


def _selected(form, name):
    """Set of selected department ids (as strings) for the checkbox cards."""
    value = form[name].value() or []
    return {str(getattr(v, "pk", v)) for v in value}


def company_admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        m = get_membership(request.user)
        if not m or m.role != "admin" or not m.company.is_approved:
            messages.error(request, "Only company administrators can manage users and departments.")
            return redirect("dashboard")
        request.company = m.company
        return view(request, *args, **kwargs)
    return wrapper


def superuser_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Only the system owner can do that.")
            return redirect("dashboard")
        return view(request, *args, **kwargs)
    return wrapper


@login_required
@require_POST
def switch_company(request):
    """Switch to another company the signed-in user is explicitly a member of."""
    company_id = request.POST.get("company_id")
    membership = user_memberships(request.user).filter(company_id=company_id).first()
    if not membership:
        messages.error(request, "You do not have access to that company.")
        return redirect("dashboard")
    request.session["active_company_id"] = membership.company_id
    request.user._erp_active_company_id = membership.company_id
    # Avoid reusing permission/membership caches from the previous workspace.
    for attr in list(vars(request.user)):
        if attr.startswith("_erp_membership_") or attr == "_erp_allowed":
            delattr(request.user, attr)
    messages.success(request, f"Switched to {membership.company.name}.")
    return redirect("dashboard")


# ------------------------------------------------------------ public registration
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = CompanyRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        approved = getattr(settings, "COMPANY_AUTO_APPROVE", False)
        company, user = form.save(approved=approved)
        login(request, user)
        if approved:
            messages.success(request, f"Welcome! {company.name} is set up.")
        return redirect("dashboard")
    return render(request, "accounts/register.html", {
        "form": form, "modules": _modules(), "selected": _selected(form, "departments"),
    })


# ------------------------------------------------------------ company admin
@company_admin_required
def team_list(request):
    members = (Membership.objects.filter(company=request.company)
               .select_related("user").prefetch_related("modules"))
    return render(request, "accounts/team_list.html", {"members": members, "company": request.company})


def _team_form(request, membership=None):
    company = request.company
    initial = {}
    if membership:
        u = membership.user
        initial = {"first_name": u.first_name, "last_name": u.last_name, "username": u.username, "email": u.email,
                   "job_title": membership.job_title, "role": membership.role, "is_active": u.is_active,
                   "departments": list(membership.modules.values_list("pk", flat=True))}
    form = TeamUserForm(request.POST or None, initial=initial, company=company, membership=membership)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        if saved.user_id == request.user.pk and form.password_changed:
            update_session_auth_hash(request, saved.user)
        messages.success(request, f"{saved.user.get_full_name() or saved.user.username} saved.")
        return redirect("accounts:team")
    return render(request, "accounts/team_form.html", {
        "form": form, "membership": membership, "modules": company.modules.all(),
        "selected": _selected(form, "departments"),
    })


@company_admin_required
def team_create(request):
    return _team_form(request)


@company_admin_required
def team_edit(request, pk):
    membership = get_object_or_404(Membership.objects.select_related("user"), pk=pk, company=request.company)
    return _team_form(request, membership)


@company_admin_required
def company_edit(request):
    form = CompanyForm(request.POST or None, request.FILES or None, instance=request.company)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Company profile and departments saved.")
        return redirect("accounts:company_edit")
    return render(request, "accounts/company_form.html", {
        "form": form, "modules": _modules(), "selected": _selected(form, "modules"),
    })


# ------------------------------------------------------------ system owner
@superuser_required
def companies(request):
    rows = Company.objects.annotate(n_users=Count("members")).prefetch_related("modules")
    return render(request, "accounts/companies.html", {"companies": rows})


@superuser_required
@require_POST
def company_toggle(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.is_approved = not company.is_approved
    company.save(update_fields=["is_approved"])
    messages.success(request, f"{company.name} {'approved' if company.is_approved else 'suspended'}.")
    return redirect("accounts:companies")


class PasswordChange(SuccessMessageMixin, auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("dashboard")
    success_message = "Your password was updated."
