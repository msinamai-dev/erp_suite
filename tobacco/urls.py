from django.urls import path
from core.crud import crud_urls, module_home
from .models import Grower, TobaccoLot, WeighingTicket, TobaccoGrade, GradeRecord, GrowerSettlement
app_name = "tobacco"
urlpatterns = [path("", module_home, name="home")]
urlpatterns += crud_urls(Grower, "grower", ["code", "name", "phone", "contract_number", "is_active"], "Growers", search=["code", "name", "phone", "contract_number"])
urlpatterns += crud_urls(TobaccoLot, "lot", ["number", "grower", "season", "received_date", "bale_count", "net_weight_kg", "status"], "Tobacco lots", search=["number", "grower__name", "season"])
urlpatterns += crud_urls(WeighingTicket, "weighing", ["number", "lot", "weighed_at", "gross_kg", "tare_kg", "net_kg"], "Weighing tickets", search=["number", "lot__number", "scale_reference"])
urlpatterns += crud_urls(TobaccoGrade, "grade", ["code", "name", "price_per_kg", "is_active"], "Tobacco grades", search=["code", "name"])
urlpatterns += crud_urls(GradeRecord, "grading", ["number", "lot", "grade", "weight_kg", "assessed_at", "assessed_by"], "Grading records", search=["number", "lot__number", "grade__name"])
urlpatterns += crud_urls(GrowerSettlement, "settlement", ["number", "grower", "lot", "settlement_date", "gross_amount", "deductions", "net_amount", "status"], "Grower settlements", search=["number", "grower__name", "payment_reference"])
