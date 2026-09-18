"""Schedule labels and exact Decimal report normalisation (52-week year convention)."""
from decimal import Decimal

FREQUENCY_LABELS={
    'daily':'Daily','weekly':'Weekly','fortnightly':'Fortnightly','four_weekly':'Every 4 weeks',
    'monthly':'Monthly','quarterly':'Quarterly','six_monthly':'Six-monthly','annually':'Annually',
    'first_day':'First day of month','last_day':'Last day of month',
}
PAYMENTS_PER_YEAR={
    'daily':Decimal(365),'weekly':Decimal(52),'fortnightly':Decimal(26),'four_weekly':Decimal(13),
    'monthly':Decimal(12),'quarterly':Decimal(4),'six_monthly':Decimal(2),'annually':Decimal(1),
    'first_day':Decimal(12),'last_day':Decimal(12),
}


def equivalents(amount, frequency):
    annual=Decimal(str(amount))*PAYMENTS_PER_YEAR[frequency]
    return annual/Decimal(12),annual
