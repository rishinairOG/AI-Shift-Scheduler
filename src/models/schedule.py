from dataclasses import dataclass, field
from datetime import date


@dataclass
class ScheduleConfig:
    restaurant_name: str
    week_start_day: str           # "SUN" or "MON"
    off_request_deadline: str     # e.g. "FRI"
    publish_day: str              # e.g. "SAT"
    start_date: date
    end_date: date
    active_shift_slots: list      # list of shift codes, e.g. ["C", "D", "E"]
    section_min_per_day: dict     # {"SERVERS": {"total": 8, "SUPERVISOR": 1}}
    section_max_off_per_day: dict # {"SERVERS": 2, "BAR": 1}
    manual_overrides: dict = field(default_factory=dict)  # {(staff_id, "YYYY-MM-DD"): "PH"|"S"|...}
    off_requests: dict = field(default_factory=dict)      # {staff_id: ["YYYY-MM-DD", ...]}
