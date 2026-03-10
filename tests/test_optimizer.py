from datetime import date, timedelta
from src.models.staff import Staff
from src.models.schedule import ScheduleConfig
from src.solver.optimizer import optimize_week, get_week_dates


def make_test_staff():
    sections = {
        "BAR": [
            Staff(id="bar_1", name="Alice", section="BAR", designation="Bartender"),
            Staff(id="bar_2", name="Bob", section="BAR", designation="Bartender"),
            Staff(id="bar_3", name="Carol", section="BAR", designation="Bartender"),
        ],
        "SERVERS": [
            Staff(id="srv_1", name="Dave", section="SERVERS", designation="Server"),
            Staff(id="srv_2", name="Eve", section="SERVERS", designation="Server"),
            Staff(id="srv_3", name="Frank", section="SERVERS", designation="Server"),
            Staff(id="srv_4", name="Grace", section="SERVERS", designation="Server"),
        ],
    }
    staff_list = [s for sec in sections.values() for s in sec]
    return staff_list, sections


def make_test_config():
    return ScheduleConfig(
        restaurant_name="Test Restaurant",
        week_start_day="SUN",
        off_request_deadline="FRI",
        publish_day="SAT",
        start_date=date(2026, 3, 8),
        end_date=date(2026, 3, 14),
        active_shift_slots=["C", "D"],
        section_min_per_day={"BAR": {"total": 2}, "SERVERS": {"total": 3}},
        section_max_off_per_day={"BAR": 1, "SERVERS": 1},
    )


def test_every_staff_gets_one_off():
    staff_list, sections = make_test_staff()
    config = make_test_config()
    week_dates = [date(2026, 3, 8) + timedelta(days=i) for i in range(7)]
    result = optimize_week(staff_list, sections, config, week_dates)

    for s in staff_list:
        off_days = [d for d in week_dates if result.get((s.id, d)) == "OFF"]
        assert len(off_days) == 1, f"{s.name} has {len(off_days)} OFF days, expected 1"


def test_same_shift_all_week():
    staff_list, sections = make_test_staff()
    config = make_test_config()
    week_dates = [date(2026, 3, 8) + timedelta(days=i) for i in range(7)]
    result = optimize_week(staff_list, sections, config, week_dates)

    for s in staff_list:
        shifts = {result.get((s.id, d)) for d in week_dates if result.get((s.id, d)) != "OFF"}
        assert len(shifts) == 1, f"{s.name} works multiple shift types: {shifts}"


def test_max_off_per_day_respected():
    staff_list, sections = make_test_staff()
    config = make_test_config()
    week_dates = [date(2026, 3, 8) + timedelta(days=i) for i in range(7)]
    result = optimize_week(staff_list, sections, config, week_dates)

    for sec_name, sec_staff in sections.items():
        max_off = config.section_max_off_per_day.get(sec_name, 1)
        for d in week_dates:
            off_count = sum(1 for s in sec_staff if result.get((s.id, d)) == "OFF")
            assert off_count <= max_off, f"{sec_name} on {d}: {off_count} OFFs > max {max_off}"


def test_manual_overrides_respected():
    staff_list, sections = make_test_staff()
    config = make_test_config()
    config.manual_overrides = {("bar_1", "2026-03-08"): "PH"}
    week_dates = [date(2026, 3, 8) + timedelta(days=i) for i in range(7)]
    result = optimize_week(staff_list, sections, config, week_dates)
    assert result.get(("bar_1", date(2026, 3, 8))) == "PH"


def test_get_week_dates():
    weeks = get_week_dates(date(2026, 3, 8), date(2026, 3, 21))
    assert len(weeks) == 2
    assert len(weeks[0]) == 7
    assert len(weeks[1]) == 7
