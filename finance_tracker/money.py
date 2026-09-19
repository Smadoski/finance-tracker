from decimal import Decimal

def convert(value, currency, base, fx):
    if isinstance(value, Decimal):
        fx = Decimal(str(fx))
    else:
        value = float(value)
    if currency == base:
        return value
    if currency == "GBP" and base == "EUR":
        return value * fx
    if currency == "EUR" and base == "GBP":
        return value / fx
    return value

def dual_values(value, currency, fx):
    value = float(value)
    if currency == "GBP":
        return value, value * fx
    return value / fx, value


def rates_in_eur(fx):
    """Expose the existing FX quote as a rate map; accept additional supplied quotes.

    This does not fetch or invent rates. Account currency groups need not assume
    that the existing GBP/EUR provider is the only possible future source.
    """
    return dict(fx) if isinstance(fx,dict) else {'EUR':1.0,'GBP':float(fx)}


def convert_known(value, currency, base, fx):
    """Strict conversion for health estimates: missing rates must never mean parity."""
    import math
    if currency==base: return float(value)
    rates=rates_in_eur(fx)
    if any(c not in rates or not math.isfinite(float(rates[c])) or float(rates[c])<=0 for c in (currency,base)):
        raise ValueError(f'No configured exchange rate for {currency} to {base}.')
    return float(value)*float(rates[currency])/float(rates[base])
