from core.crud import StyledForm

from .models import Payment


class PaymentForm(StyledForm):
    """'Record payment' form used from an invoice page (the invoice is fixed by the URL)."""

    class Meta:
        model = Payment
        fields = ["date", "amount", "method", "reference"]
