"""Generic list / create / edit / delete screens, so every model gets a consistent UI."""
from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import ProtectedError, Q
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.http import urlencode
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .models import CompanyOwned
from .tenancy import current_company_id
from .navigation import MODULES


class StyledForm(forms.ModelForm):
    """ModelForm that applies Bootstrap classes and native date pickers."""

    def _rescope(self, name, field):
        """Choice lists are built once when the URLs load (no company yet), so rebuild them for this request.

        Company-owned records are limited to the current company, the user picker to that company's people,
        and `limit_choices_to` (e.g. 'active staff only') is re-applied. The value already saved on the record
        stays selectable so editing an old task doesn't wipe its assignee.
        """
        model = field.queryset.model
        company_id = current_company_id()
        is_user = model is get_user_model()
        if not (issubclass(model, CompanyOwned) or is_user):
            return
        qs = model._default_manager.all()
        if is_user and company_id:
            qs = qs.filter(memberships__company_id=company_id)
        limit = field.get_limit_choices_to()
        if limit:
            q = Q(**limit) if isinstance(limit, dict) else limit
            current = self.initial.get(name)
            if current:
                q = q | Q(pk=getattr(current, "pk", current))
            qs = qs.filter(q)
        field.queryset = qs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field, forms.ModelChoiceField):
                self._rescope(name, field)
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"
            if isinstance(widget, forms.Textarea):
                widget.attrs["rows"] = 3
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(
                    attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"
                )


def label_for(mdl, name):
    try:
        return str(mdl._meta.get_field(name).verbose_name).capitalize()
    except FieldDoesNotExist:
        return name.replace("_", " ").capitalize()


def crud_urls(mdl, prefix, columns, title, search=(), exclude=(), row_actions=(), list_actions=(), before_list=None):
    """Return URL patterns for one model. Names: <prefix>_list/_create/_edit/_delete.

    Optional extras for the list screen:
      row_actions  - [(url_name, icon, title[, open_in_new_tab])]  extra icons on each row (url takes the row's pk)
      list_actions - [(url_name, icon, label)]                     extra buttons in the page header
      before_list  - callable run before the list loads (e.g. refresh derived statuses)
    """
    singular = str(mdl._meta.verbose_name)
    FormCls = forms.modelform_factory(
        mdl, form=StyledForm, fields="__all__", exclude=tuple(exclude) or None
    )
    slug = prefix.replace("_", "-")
    cols = list(columns)
    search_fields = list(search)
    extra_row = [{"name": n, "icon": i, "title": t, "new_tab": bool(rest and rest[0])} for n, i, t, *rest in row_actions]
    extra_list = [{"name": n, "icon": i, "label": l} for n, i, l in list_actions]

    class Ctx(LoginRequiredMixin):
        def dispatch(self, request, *args, **kwargs):
            if not request.user.is_authenticated:
                return super().dispatch(request, *args, **kwargs)
            if request.resolver_match.namespace == "procurement":
                from accounts.access import get_membership
                from procurement.access import (initiable_department_ids, is_company_admin,
                                                 is_procurement_staff)
                from procurement.models import Requisition
                membership = get_membership(request.user)
                if prefix in {"supplier", "rfq", "supplierquote", "purchaseorder", "goodsreceipt"}:
                    if not is_procurement_staff(request.user):
                        raise PermissionDenied("You are not assigned to the procurement team.")
                elif prefix == "requisition":
                    if not membership or not membership.company.is_approved:
                        raise PermissionDenied("You do not have an active company account.")
                    if self.__class__.__name__ == "CreateScreen" and not initiable_department_ids(request.user):
                        raise PermissionDenied("You have not been authorized to initiate requisitions.")
                    if self.__class__.__name__ in {"EditScreen", "DeleteScreen"} and not is_company_admin(request.user) and not is_procurement_staff(request.user):
                        raise PermissionDenied("Only company administrators or procurement staff can edit or delete requisitions.")
            return super().dispatch(request, *args, **kwargs)

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ns = self.request.resolver_match.namespace
            ctx.update(
                title=title,
                singular=singular,
                list_url=reverse(f"{ns}:{prefix}_list"),
                create_url=reverse(f"{ns}:{prefix}_create"),
            )
            return ctx

    class ListScreen(Ctx, ListView):
        model = mdl
        paginate_by = 15
        template_name = "core/list.html"

        def post(self, request, *args, **kwargs):
            """Handle bulk deletion only on list pages, not create/edit forms."""
            if prefix == "requisition":
                from procurement.access import is_company_admin, is_procurement_staff
                if not (is_company_admin(request.user) or is_procurement_staff(request.user)):
                    raise PermissionDenied("You are not authorized to delete requisitions.")
            ids = [i for i in request.POST.getlist("ids") if i.isdigit()]
            ns = request.resolver_match.namespace
            url = reverse(f"{ns}:{prefix}_list")
            q = request.GET.get("q", "").strip()
            if q:
                url += "?" + urlencode({"q": q})
            if not ids:
                messages.warning(request, "No records selected.")
                return redirect(url)
            deleted = blocked = 0
            for obj in mdl._default_manager.filter(pk__in=ids):
                try:
                    obj.delete()
                    deleted += 1
                except ProtectedError:
                    blocked += 1
            if deleted:
                messages.success(request, f"Deleted {deleted} record{'s' if deleted != 1 else ''}.")
            if blocked:
                messages.error(
                    request,
                    f"{blocked} record{'s' if blocked != 1 else ''} used by other records, so couldn't be deleted.",
                )
            return redirect(url)

        def get_queryset(self):
            if before_list:
                before_list()
            qs = super().get_queryset()
            if prefix == "requisition":
                from procurement.access import visible_requisitions
                qs = visible_requisitions(self.request.user, qs)
            fks = [f.name for f in mdl._meta.get_fields() if getattr(f, "many_to_one", False) and f.concrete]
            if fks:
                qs = qs.select_related(*fks)
            q = self.request.GET.get("q", "").strip()
            if q and search_fields:
                cond = Q()
                for s in search_fields:
                    cond |= Q(**{f"{s}__icontains": q})
                qs = qs.filter(cond)
            return qs

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            ns = self.request.resolver_match.namespace
            can_manage = True
            can_create = True
            if prefix == "requisition":
                from procurement.access import initiable_department_ids, is_company_admin, is_procurement_staff
                can_manage = bool(is_company_admin(self.request.user) or is_procurement_staff(self.request.user))
                can_create = bool(initiable_department_ids(self.request.user))
            if prefix == "requisition":
                from procurement.access import can_approve_requisition, is_company_admin
                rows = ctx.get("object_list", [])
                ctx["requisition_screen"] = True
                ctx["approvable_ids"] = {
                    obj.pk for obj in rows
                    if obj.status == "pending" and can_approve_requisition(self.request.user, obj)
                    and (is_company_admin(self.request.user) or obj.created_by_id != self.request.user.pk)
                }
            else:
                ctx["requisition_screen"] = False
                ctx["approvable_ids"] = set()
            ctx.update(
                columns=[(c, label_for(mdl, c)) for c in cols],
                q=self.request.GET.get("q", ""),
                searchable=bool(search_fields),
                edit_name=f"{ns}:{prefix}_edit",
                delete_name=f"{ns}:{prefix}_delete",
                row_actions=[{**a, "name": f"{ns}:{a['name']}"} for a in extra_row],
                list_actions=[{**a, "url": reverse(f"{ns}:{a['name']}")} for a in extra_list],
                can_manage=can_manage,
                can_create=can_create,
            )
            return ctx

    class SaveMixin(Ctx):
        model = mdl
        form_class = FormCls
        template_name = "core/form.html"

        def get_form(self, form_class=None):
            form = super().get_form(form_class)
            if prefix in {"requisition", "rfq", "purchaseorder"} and "status" in form.fields:
                # Workflow states change only through the permission-checked action endpoints.
                form.fields.pop("status")
            if prefix == "requisition":
                from accounts.access import get_membership
                from accounts.models import Module
                from procurement.access import initiable_department_ids, is_company_admin, is_procurement_staff
                ids = initiable_department_ids(self.request.user)
                if self.request.resolver_match.url_name != "requisition_create" and (is_company_admin(self.request.user) or is_procurement_staff(self.request.user)):
                    membership = get_membership(self.request.user)
                    ids = list(membership.company.modules.values_list("pk", flat=True)) if membership else []
                if "department" in form.fields:
                    form.fields["department"].queryset = Module.objects.filter(pk__in=ids)
                    form.fields["department"].required = True
                if self.request.resolver_match.url_name == "requisition_create" and "requested_by" in form.fields:
                    from hr.models import Employee
                    employee = Employee.objects.filter(user=self.request.user, status="active").first()
                    if employee:
                        form.fields["requested_by"].initial = employee.pk
                        form.fields["requested_by"].queryset = Employee.objects.filter(pk=employee.pk)
                        form.fields["requested_by"].widget = forms.HiddenInput()
            return form

        def get_success_url(self):
            return reverse(f"{self.request.resolver_match.namespace}:{prefix}_list")

        def form_valid(self, form):
            if prefix == "requisition":
                from procurement.access import can_initiate_in
                if self.request.resolver_match.url_name == "requisition_create":
                    if not can_initiate_in(self.request.user, form.instance.department_id):
                        raise PermissionDenied("You cannot initiate requisitions for this department.")
                    form.instance.created_by = self.request.user
                    from hr.models import Employee
                    employee = Employee.objects.filter(user=self.request.user, status="active").first()
                    if employee:
                        form.instance.requested_by = employee
            messages.success(self.request, f"{singular.capitalize()} saved.")
            return super().form_valid(form)

    class CreateScreen(SaveMixin, CreateView):
        pass

    class EditScreen(SaveMixin, UpdateView):
        pass

    class DeleteScreen(Ctx, DeleteView):
        model = mdl
        template_name = "core/confirm_delete.html"

        def get_success_url(self):
            return reverse(f"{self.request.resolver_match.namespace}:{prefix}_list")

        def form_valid(self, form):
            try:
                self.object.delete()
                messages.success(self.request, f"{singular.capitalize()} deleted.")
            except ProtectedError:
                messages.error(
                    self.request,
                    f"This {singular} is used by other records, so it can't be deleted.",
                )
            return redirect(self.get_success_url())

    return [
        path(f"{slug}/", ListScreen.as_view(), name=f"{prefix}_list"),
        path(f"{slug}/new/", CreateScreen.as_view(), name=f"{prefix}_create"),
        path(f"{slug}/<int:pk>/edit/", EditScreen.as_view(), name=f"{prefix}_edit"),
        path(f"{slug}/<int:pk>/delete/", DeleteScreen.as_view(), name=f"{prefix}_delete"),
    ]


@login_required
def module_home(request):
    """Landing page for a module: one tile per screen, with record counts."""
    ns = request.resolver_match.namespace
    module = next(m for m in MODULES if m["key"] == ns)
    tiles = []
    for item in module["items"]:
        count = apps.get_model(item["model"]).objects.count() if item["model"] else None
        target_ns = item.get("namespace", ns)
        create = None
        if item["url"].endswith("_list"):
            create = reverse(f"{target_ns}:{item['url'].replace('_list', '_create')}")
        tiles.append({**item, "count": count, "href": reverse(f"{target_ns}:{item['url']}"), "create": create})
    return render(request, "core/module_home.html", {"module": module, "tiles": tiles})
