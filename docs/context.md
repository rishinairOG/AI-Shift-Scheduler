# AI Shift Scheduler — Project Context

## Why This Exists

Built by Rishi Nair (7 years F&B operations, White Robata KSA) to replace the manual Excel-based duty scheduling process. A manager currently spends significant time each week distributing shift assignments across 40+ staff, enforcing per-section coverage rules, managing OFF day fairness, and exporting an Excel grid. This tool automates that entire process via a constraint solver, guided by a setup wizard that collects the right operational inputs upfront.

The output matches the existing Excel format already in use — so it fits directly into the current workflow without retraining staff.

---

## Real Roster Reference

Source file used to infer format:
`C:/Users/rishi/OneDrive/Desktop/WR KSA/WR_FOH/FOH WR KSA/Duty roster - New Format.xlsx`

**Sheet:** `dec`
**Format:** Rows = staff grouped by section, Columns = dates, Cells = shift code or status code
**Coverage rows:** Bottom of sheet — COUNTIF summaries per time window per day

---

## Sections (from real roster)

| Section | Staff Count | Notes |
|---|---|---|
| MANAGERS | 1 | |
| ASST. MANAGERS | 1 | Interchangeable with Managers/Supervisors for shift assignment |
| SUPERVISORS | 2 | Interchangeable with Managers/Asst. Managers |
| SERVERS | 15 | Largest section; most scheduling complexity |
| GRE (Hostess) | 2 | Guest Relations Executives |
| BAR | 3 | |
| Housekeeping | 2 | Same rules as FOH |

**Total: ~ staff**

---

## Standard Shift Slots (all exactly 9 hours, no overtime)

| Code | Shift | Hours |
|---|---|---|
| A | 9AM – 6PM | 9 |
| B | 11AM – 8PM | 9 |
| C | 1PM – 10PM | 9 |
| D | 3PM – 12AM | 9 |
| E | 5:30PM – 2:30AM | 9 |
| F | 6PM – 3AM | 9 |

Manager selects which slots are active per schedule instance.

---

## Status Codes

| Code | Meaning | Who Sets It |
|---|---|---|
| OFF | Weekly day off | AI-generated |
| PH | Public Holiday | Manager (manual) |
| HP | Half Public Holiday | Manager (manual) |
| S | Sick Leave | Manager (manual) |
| HD | Half Day | Manager (manual) |
| HO | Half Off Day | Manager (manual) |
| TR | Transferred | Manager (manual) |
| V | Vacation | Manager (manual) |

Manual statuses override AI assignment for that cell — the optimizer never touches them.

---

## Hard Constraints

| Priority | Constraint |
|---|---|
| 1 | Manual overrides (PH, S, V, TR, HD, HO) — optimizer never changes these |
| 2 | Section min coverage per shift must be met |
| 3 | Exactly 1 OFF per staff per 7-day week |
| 4 | Staff assigned to the same shift slot every working day of the week |
| 5 | OFF by Wednesday rule (see below) |
| 6 | Max OFF per day per section |
| 7 (soft) | Honor staff OFF requests |
| 8 (soft) | Fair rotation of shift slots across weeks |

### OFF Distribution Rule ("by Wednesday")
- **Small section (≤6 staff):** max 1 OFF per day — all OFFs done by Tuesday/Wednesday
- **Large section (>6 staff, e.g. SERVERS 19):** max 2 OFF Sun–Tue, max 1 OFF Wed–Sat
- Goal: full manning from Wednesday onward each week

### Shift Consistency Rule
- Each staff member stays on the same shift slot for the entire week
- Reason: sleep balance and routine for the employee

---

## Per-Instance Questions (asked before each schedule generation)

1. Schedule start date and end date (manager chooses freely)
2. Which shift slots are active this period (subset of A–F)
3. For each section: min total staff per shift
4. For each section: min per designation per shift (e.g. ≥1 Manager per shift)
5. For each section: max OFF per day
6. Manual overrides for the period (staff × date → status code)
7. Staff OFF requests (must be submitted by deadline day)

---

## One-Time Setup Questions (per restaurant)

1. Restaurant name
2. Week start day — Sunday (Middle East) or Monday (Western)
3. OFF request deadline day (e.g. Friday)
4. Schedule publish day (e.g. Saturday)
5. Staff roster (upload existing Excel or manual entry)

---

## Application Flow

```
[Upload Roster] → [Setup Wizard] → [Per-Schedule Form]
       → [Constraint Optimizer] → [Preview + Warnings] → [Download .xlsx]
```

---

## Project Structure

```
AI Shift Scheduler/
├── src/
│   ├── models/             # Typed data models (Staff, ShiftSlot, ScheduleConfig)
│   │   ├── staff.py
│   │   ├── section.py
│   │   ├── shift.py
│   │   └── schedule.py
│   ├── solver/             # OR-Tools constraint optimizer
│   │   └── optimizer.py
│   ├── parser/             # Excel roster ingestion (openpyxl)
│   │   └── roster_parser.py
│   ├── exporter/           # Excel output generation
│   │   └── excel_exporter.py
│   └── ui/                 # Streamlit pages
│       ├── setup_wizard.py
│       ├── schedule_form.py
│       └── preview.py
├── tests/
│   ├── test_optimizer.py
│   ├── test_parser.py
│   └── test_exporter.py
├── docs/
│   └── context.md          ← this file
├── config/
│   └── defaults.py
├── examples/
│   └── sample_roster.xlsx
├── app.py                  # Streamlit entry point
└── requirements.txt
```

---

## Tech Stack

| Layer | Library | Reason |
|---|---|---|
| Frontend | Streamlit | Fast to ship, no JS needed |
| Optimizer | OR-Tools (ortools) | Industry-grade constraint solver (ILP) |
| Excel I/O | openpyxl | Read/write .xlsx matching existing format |
| Data models | Python dataclasses | Typed, lightweight |
| Testing | pytest | Standard |

---

## Key Data Models

### Staff
```python
@dataclass
class Staff:
    id: str
    name: str
    section: str          # e.g. "SERVERS", "BAR"
    designation: str      # e.g. "Server", "Supervisor"
    fixed_off_day: str | None  # e.g. "SUN" — stays fixed unless changed
```

### ShiftSlot
```python
@dataclass
class ShiftSlot:
    code: str       # "A" through "F"
    start_time: str # "09:00"
    end_time: str   # "18:00"
    label: str      # "9AM – 6PM"
```

### ScheduleConfig
```python
@dataclass
class ScheduleConfig:
    restaurant_name: str
    week_start_day: str            # "SUN" or "MON"
    off_request_deadline: str      # "FRI"
    publish_day: str               # "SAT"
    start_date: date
    end_date: date
    active_shift_slots: list       # subset of ["A","B","C","D","E","F"]
    section_min_per_day: dict      # {"SERVERS": {"total": 8, "Supervisor": 1}}
    section_max_off_per_day: dict  # {"SERVERS": 2, "BAR": 1}
    manual_overrides: dict = ...   # {(staff_id, "YYYY-MM-DD"): "PH"|"S"|"HD"|"V"|"TR"|"HO"}
    off_requests: dict = ...       # {staff_id: ["YYYY-MM-DD", ...]}
```

**Important:** `manual_overrides` keys use `"YYYY-MM-DD"` string dates, not `date` objects. `section_min_per_day` is named per-day (not per-shift) — the minimum is enforced across all active shifts on that day.

---

## Verification Plan

1. Unit test optimizer with the real 43-staff roster → assert all hard constraints satisfied
2. Unit test roster parser against `Duty roster - New Format.xlsx` → verify section/staff extraction
3. Unit test Excel exporter → open output and compare cell values to expected
4. End-to-end Streamlit test: upload roster → configure → generate → download
5. Manual visual check: open exported .xlsx and compare layout to existing format

---

## Test Status

**11/11 tests passing** as of 2026-03-09.

| Test File | Tests | Status |
|---|---|---|
| `tests/test_optimizer.py` | 5 | ✅ All passing |
| `tests/test_parser.py` | 4 | ✅ All passing (against real roster file) |
| `tests/test_exporter.py` | 2 | ✅ All passing |

Run tests: `python -m pytest tests/ -v` from project root.

**End-to-end verification (2026-03-10):**
- ✅ App launched: `streamlit run app.py --server.headless true`
- ✅ Setup wizard: "White Robata KSA", SUN start, FRI deadline, SAT publish
- ✅ Roster upload: `Duty roster_Experiment.xlsx` → 43 staff across 7 sections parsed correctly
- ✅ Schedule generated: 2026-03-10 to 2026-03-16, shifts C + D, solver completed
- ✅ Preview rendered: color-coded grid (grey=OFF, green=shift), section headers, date columns
- ✅ Download: `.xlsx` file exported successfully

**11 warnings** (expected with default constraints):
- MANAGERS: 0 working on Tue 10 (only 1 staff, took OFF that day)
- SERVERS: 3 OFFs on 5 days (max configured = 2) — reduce min or increase max OFF to resolve

**Remaining:** visual comparison of exported `.xlsx` layout vs original `Duty roster - New Format.xlsx`

---

## Launch

```bash
cd "C:/Users/rishi/AI Shift Scheduler"
streamlit run app.py --server.headless true
```

*Last updated: 2026-03-10 — E2E verification complete*
