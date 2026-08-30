def display_report_values(amount, currency, fx, kind, dual_values_fn):
    gbp, eur = dual_values_fn(amount, currency, fx)
    if kind == "expense":
        gbp, eur = abs(gbp), abs(eur)
    return gbp, eur
