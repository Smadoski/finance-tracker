def convert(value, currency, base, fx):
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
