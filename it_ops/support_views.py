from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.access import get_membership
from accounts.models import Membership
from hr.models import Department, Employee
from .models import Ticket, TicketComment


def _context(request):
    membership = get_membership(request.user)
    if not membership:
        raise PermissionDenied("Your account is not linked to a company.")
    company = membership.company
    if not company.it_support_enabled:
        raise PermissionDenied("IT support is disabled for this company.")
    employee = Employee._base_manager.filter(user=request.user, company=company, status="active").first()
    is_it = request.user.is_superuser or membership.role == "admin" or membership.modules.filter(key="it_ops").exists()
    return membership, company, employee, is_it


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "department", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, company, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department._base_manager.filter(company=company)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
        self.fields["department"].required = False


@login_required
def ticket_list(request):
    membership, company, employee, is_it = _context(request)
    tickets = Ticket._base_manager.filter(company=company).select_related("requested_by", "requested_by_user", "department")
    view_all = request.GET.get("scope") == "all" and is_it
    if not view_all:
        if employee:
            from django.db.models import Q
            tickets = tickets.filter(Q(requested_by_user=request.user) | Q(requested_by=employee))
        else:
            tickets = tickets.filter(requested_by_user=request.user)
    return render(request, "it_ops/support_list.html", {
        "tickets": tickets, "is_it": is_it, "view_all": view_all,
        "employee": employee, "company": company,
    })


@login_required
def ticket_create(request):
    membership, company, employee, is_it = _context(request)
    form = TicketCreateForm(request.POST or None, company=company)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.company = company
        ticket.requested_by = employee
        ticket.requested_by_user = request.user
        if ticket.department_id and ticket.department.company_id != company.pk:
            raise PermissionDenied("Invalid department.")
        ticket.save()
        TicketComment.objects.create(company=company, ticket=ticket, author=request.user,
                                     message="Ticket created.", is_internal=False)
        messages.success(request, f"Ticket {ticket.number} has been submitted.")
        return redirect("support:detail", pk=ticket.pk)
    return render(request, "it_ops/support_form.html", {"form": form})


@login_required
def ticket_detail(request, pk):
    membership, company, employee, is_it = _context(request)
    ticket = get_object_or_404(Ticket._base_manager.select_related("requested_by", "requested_by_user", "department"), pk=pk, company=company)
    if not is_it and (not employee or ticket.requested_by_id != employee.pk):
        raise PermissionDenied("You can only view tickets you submitted.")
    comments = ticket.comments.select_related("author")
    if not is_it:
        comments = comments.filter(is_internal=False)
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if message:
            TicketComment.objects.create(company=company, ticket=ticket, author=request.user,
                                         message=message, is_internal=False)
            messages.success(request, "Your update has been added.")
        return redirect("support:detail", pk=ticket.pk)
    return render(request, "it_ops/support_detail.html", {
        "ticket": ticket, "comments": comments, "is_it": is_it,
        "status_choices": Ticket.STATUS, "priority_choices": Ticket.PRIORITY,
    })


@login_required
@require_POST
def ticket_update(request, pk):
    membership, company, employee, is_it = _context(request)
    if not is_it:
        raise PermissionDenied("Only authorized IT staff can update ticket status or assignment.")
    with transaction.atomic():
        ticket = get_object_or_404(Ticket.objects.select_for_update(), pk=pk, company=company)
        old_status = ticket.status
        old_priority = ticket.priority
        old_assignee = ticket.assigned_to
        ticket.status = request.POST.get("status", ticket.status)
        ticket.priority = request.POST.get("priority", ticket.priority)
        ticket.assigned_to = request.POST.get("assigned_to", ticket.assigned_to).strip()[:120]
        if ticket.status not in dict(Ticket.STATUS) or ticket.priority not in dict(Ticket.PRIORITY):
            messages.error(request, "Invalid status or priority.")
            return redirect("support:detail", pk=ticket.pk)
        ticket.save(update_fields=["status", "priority", "assigned_to"])
        changes = []
        if old_status != ticket.status: changes.append(f"Status changed from {old_status} to {ticket.status}.")
        if old_priority != ticket.priority: changes.append(f"Priority changed from {old_priority} to {ticket.priority}.")
        if old_assignee != ticket.assigned_to: changes.append(f"Assigned technician changed to {ticket.assigned_to or 'Unassigned'}.")
        note = request.POST.get("internal_note", "").strip()
        if note:
            TicketComment.objects.create(company=company, ticket=ticket, author=request.user, message=note, is_internal=True)
        if changes:
            TicketComment.objects.create(company=company, ticket=ticket, author=request.user,
                                         message=" ".join(changes), is_internal=False)
    messages.success(request, "Ticket updated.")
    return redirect("support:detail", pk=ticket.pk)
