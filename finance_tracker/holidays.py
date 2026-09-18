"""Offline bank calendars. UK means England/Wales; see HOLIDAY-CALENDARS.md."""
from datetime import date, timedelta
from functools import lru_cache

CALENDARS = {'weekdays': 'Weekdays only', 'uk': 'UK working days (England & Wales)', 'cyprus': 'Cyprus working days'}


def easter(year, orthodox=False):
    if orthodox:
        a, b, c = year % 4, year % 7, year % 19
        d = (19*c+15) % 30
        e = (2*a+4*b-d+34) % 7
        return date(year, (d+e+114)//31, (d+e+114)%31+1) + timedelta(days=year//100-year//400-2)
    a=year%19; b=year//100; c=year%100; d=b//4; e=b%4
    f=(b+8)//25; g=(b-f+1)//3; h=(19*a+b-d-g+15)%30
    i=c//4; k=c%4; l=(32+2*e+2*i-h-k)%7; m=(a+11*h+22*l)//451
    return date(year,(h+l-7*m+114)//31,(h+l-7*m+114)%31+1)


@lru_cache(maxsize=256)
def holidays(year, calendar):
    if calendar not in CALENDARS: raise ValueError('Unknown working-day calendar.')
    if calendar == 'weekdays': return frozenset()
    if not 1900 <= year <= 2099: raise ValueError('Bank calendars support 1900–2099.')
    pascha=easter(year, calendar=='cyprus')
    if calendar=='cyprus':
        fixed={(1,1),(1,6),(3,25),(4,1),(5,1),(8,15),(10,1),(10,28),(12,25),(12,26)}
        return frozenset({date(year,m,d) for m,d in fixed} | {pascha+timedelta(days=n) for n in (-48,-2,1,2,50)})
    days={pascha-timedelta(days=2),pascha+timedelta(days=1)}
    for month,day in ((1,1),(12,25),(12,26)):
        value=date(year,month,day)
        while value.weekday()>=5 or value in days: value+=timedelta(days=1)
        days.add(value)
    for month,day,last in ((5,1,False),(5,31,True),(8,31,True)):
        value=date(year,month,day)
        value+=timedelta(days= -value.weekday() if last else (-value.weekday())%7)
        days.add(value)
    if year==2020: days.remove(date(2020,5,4)); days.add(date(2020,5,8))
    if year==2022:
        days.remove(date(2022,5,30)); days.update({date(2022,6,2),date(2022,6,3),date(2022,9,19)})
    if year==2023: days.add(date(2023,5,8))
    return frozenset(days)


def is_working_day(value, calendar='weekdays'):
    return value.weekday()<5 and value not in holidays(value.year,calendar)
