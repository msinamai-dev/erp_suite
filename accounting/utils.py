"""Small helpers for the accounting module."""
from decimal import ROUND_HALF_UP, Decimal

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_SCALES = [(10 ** 9, "billion"), (10 ** 6, "million"), (10 ** 3, "thousand")]


def _under_1000(n):
    parts = []
    if n >= 100:
        parts.append(f"{_ONES[n // 100]} hundred")
        n %= 100
        if n:
            parts.append("and")
    if n >= 20:
        parts.append(_TENS[n // 10] + (f"-{_ONES[n % 10]}" if n % 10 else ""))
    elif n or not parts:
        parts.append(_ONES[n])
    return " ".join(parts)


def number_to_words(n):
    if n == 0:
        return "zero"
    parts = []
    for size, name in _SCALES:
        if n >= size:
            parts.append(f"{_under_1000(n // size)} {name}")
            n %= size
    if n:
        # "one thousand and five", "two million one hundred" read naturally in invoices
        parts.append(("and " if parts and n < 100 else "") + _under_1000(n))
    return " ".join(parts)


def amount_in_words(amount, currency_name="dollars"):
    """1250.5 -> 'One thousand two hundred and fifty dollars and 50/100 only'."""
    amount = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole, cents = divmod(int(abs(amount) * 100), 100)
    text = number_to_words(whole)
    return f"{text[:1].upper()}{text[1:]} {currency_name} and {cents:02d}/100 only"
