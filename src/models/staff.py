from dataclasses import dataclass


@dataclass
class Staff:
    id: str
    name: str
    section: str
    designation: str
    fixed_off_day: str | None = None  # e.g. "SUN" — stays fixed unless changed
