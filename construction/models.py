from decimal import Decimal

from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Sum

from core.models import CompanyOwned, Numbered, money


class Project(Numbered):
    PREFIX = "PRJ"
    STATUS = [("planning", "Planning"), ("in_progress", "In progress"),
              ("on_hold", "On hold"), ("completed", "Completed")]

    name = models.CharField(max_length=200)
    client = models.ForeignKey("sales.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    site_location = models.CharField(max_length=200, blank=True)
    manager = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={"status": "active"},
                                related_name="managed_projects", verbose_name="project manager")
    budget = money()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Planned completion date")
    status = models.CharField(max_length=12, choices=STATUS, default="planning")
    progress = models.PositiveSmallIntegerField("progress %", default=0, validators=[MaxValueValidator(100)])
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-id"]

    @property
    def spent(self):
        """Approved or paid expenses charged to this project."""
        total = self.expenses.filter(status__in=["approved", "paid"]).aggregate(t=Sum("amount"))["t"]
        return total or Decimal("0")

    @property
    def budget_used(self):
        return int(self.spent * 100 / self.budget) if self.budget else 0

    def __str__(self):
        return f"{self.number} {self.name}"


class ProjectTask(CompanyOwned):
    STATUS = [("todo", "To do"), ("in_progress", "In progress"), ("blocked", "Blocked"), ("done", "Done")]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=200)
    assigned_to = models.ForeignKey("hr.Employee", on_delete=models.SET_NULL, null=True, blank=True,
                                    limit_choices_to={"status": "active"})
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    progress = models.PositiveSmallIntegerField("progress %", default=0, validators=[MaxValueValidator(100)])
    status = models.CharField(max_length=12, choices=STATUS, default="todo")

    class Meta:
        ordering = ["due_date"]
        verbose_name = "task"

    def __str__(self):
        return self.name


class Subcontract(Numbered):
    PREFIX = "SUB"
    STATUS = [("draft", "Draft"), ("active", "Active"), ("completed", "Completed"), ("terminated", "Terminated")]

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    contractor = models.CharField(max_length=200)
    scope = models.CharField("scope of work", max_length=250)
    contract_value = money()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.number} {self.contractor}"
