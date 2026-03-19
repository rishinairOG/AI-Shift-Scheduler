"""Tests for src/rag/schedule_summary.py — pure stats builder."""

from datetime import date

from src.models.staff import Staff
from src.models.schedule import ScheduleConfig
from src.rag.schedule_summary import build_summary_stats


def _make_fixture():
    sections = {
        "BAR": [
            Staff(id="bar_1", name="Alice", section="BAR", designation="Bartender"),
            Staff(id="bar_2", name="Bob", section="BAR", designation="Bartender"),
            Staff(id="bar_3", name="Carol", section="BAR", designation="Bartender"),
        ],
    }
    staff_list = sections["BAR"]
    config = ScheduleConfig(
        restaurant_name="Test Café",
        week_start_day="SUN",
        off_request_deadline="FRI",
        publish_day="SAT",
        start_date=date(2026, 3, 15),
        end_date=date(2026, 3, 21),
        active_shift_slots=["C", "D"],
        section_min_per_day={"BAR": {"total": 2}},
        section_max_off_per_day={"BAR": 1},
    )
    assignments = {
        ("bar_1", date(2026, 3, 15)): "C",
        ("bar_1", date(2026, 3, 16)): "OFF",
        ("bar_1", date(2026, 3, 17)): "C",
        ("bar_1", date(2026, 3, 18)): "C",
        ("bar_1", date(2026, 3, 19)): "C",
        ("bar_1", date(2026, 3, 20)): "C",
        ("bar_1", date(2026, 3, 21)): "C",
        ("bar_2", date(2026, 3, 15)): "OFF",
        ("bar_2", date(2026, 3, 16)): "D",
        ("bar_2", date(2026, 3, 17)): "D",
        ("bar_2", date(2026, 3, 18)): "D",
        ("bar_2", date(2026, 3, 19)): "D",
        ("bar_2", date(2026, 3, 20)): "D",
        ("bar_2", date(2026, 3, 21)): "D",
        ("bar_3", date(2026, 3, 15)): "C",
        ("bar_3", date(2026, 3, 16)): "C",
        ("bar_3", date(2026, 3, 17)): "OFF",
        ("bar_3", date(2026, 3, 18)): "C",
        ("bar_3", date(2026, 3, 19)): "C",
        ("bar_3", date(2026, 3, 20)): "C",
        ("bar_3", date(2026, 3, 21)): "C",
    }
    return staff_list, sections, config, assignments


class TestBuildSummaryStats:
    def test_contains_restaurant_and_period(self):
        staff, sections, config, assignments = _make_fixture()
        stats = build_summary_stats(staff, sections, config, assignments)
        assert "Test Café" in stats
        assert "2026-03-15" in stats
        assert "2026-03-21" in stats

    def test_contains_section_info(self):
        staff, sections, config, assignments = _make_fixture()
        stats = build_summary_stats(staff, sections, config, assignments)
        assert "BAR" in stats
        assert "3 staff" in stats

    def test_contains_shift_codes(self):
        staff, sections, config, assignments = _make_fixture()
        stats = build_summary_stats(staff, sections, config, assignments)
        assert "C:" in stats
        assert "D:" in stats

    def test_contains_off_distribution(self):
        staff, sections, config, assignments = _make_fixture()
        stats = build_summary_stats(staff, sections, config, assignments)
        assert "OFFs by day-of-week" in stats

    def test_empty_assignments(self):
        staff, sections, config, _ = _make_fixture()
        stats = build_summary_stats(staff, sections, config, {})
        assert "Test Café" in stats
        assert "BAR" in stats
