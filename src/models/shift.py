from dataclasses import dataclass


STANDARD_SHIFT_SLOTS = [
    {"code": "A", "start_time": "09:00", "end_time": "18:00", "label": "9AM \u2013 6PM"},
    {"code": "B", "start_time": "11:00", "end_time": "20:00", "label": "11AM \u2013 8PM"},
    {"code": "C", "start_time": "13:00", "end_time": "22:00", "label": "1PM \u2013 10PM"},
    {"code": "D", "start_time": "15:00", "end_time": "00:00", "label": "3PM \u2013 12AM"},
    {"code": "E", "start_time": "17:30", "end_time": "02:30", "label": "5:30PM \u2013 2:30AM"},
    {"code": "F", "start_time": "18:00", "end_time": "03:00", "label": "6PM \u2013 3AM"},
]


@dataclass
class ShiftSlot:
    code: str
    start_time: str
    end_time: str
    label: str
