"""Tee time utility functions — seasonal hours and generation."""
from datetime import time, timedelta


def get_seasonal_hours(target_date):
    """Return (start_hour, start_min, end_hour, end_min) for the given date.

    April–September:  07:00 – 20:30
    October–March:    08:00 – 15:30
    """
    month = target_date.month
    if 4 <= month <= 9:
        return 7, 0, 20, 30
    else:
        return 8, 0, 15, 30


def generate_tee_time_slots(target_date, interval_minutes=10):
    """Return a list of datetime.time objects for general play on the given date."""
    start_h, start_m, end_h, end_m = get_seasonal_hours(target_date)
    slots = []
    h, m = start_h, start_m
    while (h, m) <= (end_h, end_m):
        slots.append(time(h, m))
        m += interval_minutes
        if m >= 60:
            h += 1
            m -= 60
    return slots


def generate_comp_tee_time_slots(target_date, interval_minutes=10):
    """Return a list of datetime.time objects for competition tee times.

    Starts from the first seasonal hour and ends at 11:50.
    """
    start_h, start_m, _, _ = get_seasonal_hours(target_date)
    end_h, end_m = 11, 50
    slots = []
    h, m = start_h, start_m
    while (h, m) <= (end_h, end_m):
        slots.append(time(h, m))
        m += interval_minutes
        if m >= 60:
            h += 1
            m -= 60
    return slots
