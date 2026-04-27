"""Unit tests for utility services."""
from datetime import date, time
from app.services.tee_time_utils import (
    get_seasonal_hours,
    generate_tee_time_slots,
    generate_comp_tee_time_slots,
    generate_range_bay_slots
)


def test_summer_hours():
    """Test get_seasonal_hours returns summer hours for July."""
    target = date(2025, 7, 15)
    sh, sm, eh, em = get_seasonal_hours(target)
    assert (sh, sm) == (7, 0)
    assert (eh, em) == (20, 30)


def test_winter_hours():
    """Test get_seasonal_hours returns winter hours for December."""
    target = date(2025, 12, 15)
    sh, sm, eh, em = get_seasonal_hours(target)
    assert (sh, sm) == (8, 0)
    assert (eh, em) == (15, 30)


def test_generate_tee_time_slots_summer():
    """Test generate_tee_time_slots for summer."""
    target = date(2025, 7, 15)
    slots = generate_tee_time_slots(target)
    assert len(slots) > 0
    assert slots[0] == time(7, 0)
    assert slots[-1] == time(20, 30)


def test_generate_tee_time_slots_winter():
    """Test generate_tee_time_slots for winter."""
    target = date(2025, 12, 15)
    slots = generate_tee_time_slots(target)
    assert len(slots) > 0
    assert slots[0] == time(8, 0)
    assert slots[-1] == time(15, 30)


def test_generate_comp_slots_summer():
    """Test generate_comp_tee_time_slots for summer."""
    target = date(2025, 7, 15)
    slots = generate_comp_tee_time_slots(target)
    assert len(slots) > 0
    assert slots[0] == time(7, 0)
    assert slots[-1] == time(11, 50)


def test_generate_comp_slots_winter():
    """Test generate_comp_tee_time_slots for winter."""
    target = date(2025, 12, 15)
    slots = generate_comp_tee_time_slots(target)
    assert len(slots) > 0
    assert slots[0] == time(8, 0)
    assert slots[-1] == time(11, 50)


def test_generate_range_bay_slots_summer():
    """Test generate_range_bay_slots for summer."""
    target = date(2025, 7, 15)
    slots = generate_range_bay_slots(target)
    assert len(slots) > 0
    assert slots[0] == time(7, 0)
    assert slots[-1] == time(20, 30)


def test_generate_range_bay_slots_winter():
    """Test generate_range_bay_slots for winter."""
    target = date(2025, 12, 15)
    slots = generate_range_bay_slots(target)
    assert len(slots) > 0
    assert slots[0] == time(8, 0)
    assert slots[-1] == time(15, 30)
