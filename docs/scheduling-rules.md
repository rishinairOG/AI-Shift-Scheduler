# Scheduling Rules — Policy Reference

This document defines the **scheduling rules and policy** used by the AI Shift Scheduler. It is the single source of truth for in-app help and RAG Q&A. Project and technical details live in `context.md`.

---

## Standard Shift Slots (all exactly 9 hours, no overtime)

| Code | Shift | Hours |
|------|-------|-------|
| A | 9AM – 6PM | 9 |
| B | 11AM – 8PM | 9 |
| C | 1PM – 10PM | 9 |
| D | 3PM – 12AM | 9 |
| E | 5:30PM – 2:30AM | 9 |
| F | 6PM – 3AM | 9 |

The manager selects which shift slots are **active** for each schedule period (subset of A–F).

---

## Status Codes

| Code | Meaning | Who Sets It |
|------|---------|-------------|
| OFF | Weekly day off | AI-generated |
| PH | Public Holiday | Manager (manual) |
| HP | Half Public Holiday | Manager (manual) |
| S | Sick Leave | Manager (manual) |
| HD | Half Day | Manager (manual) |
| HO | Half Off Day | Manager (manual) |
| TR | Transferred | Manager (manual) |
| V | Vacation | Manager (manual) |

**Rule:** Manual statuses (PH, S, V, TR, HD, HO, HP) override the AI assignment for that cell. The optimizer never changes them.

---

## Hard Constraints (priority order)

| Priority | Constraint |
|----------|------------|
| 1 | Manual overrides (PH, S, V, TR, HD, HO) — optimizer never changes these |
| 2 | Section min coverage per day must be met (across all active shifts that day) |
| 3 | Exactly 1 OFF per staff per 7-day week |
| 4 | Staff assigned to the same shift slot every working day of the week |
| 5 | OFF by Wednesday rule (see below) |
| 6 | Max OFF per day per section (configured per section) |
| 7 (soft) | Honor staff OFF requests where possible |
| 8 (soft) | Fair rotation of shift slots across weeks |

---

## OFF Distribution Rule ("by Wednesday")

- **Small section (≤6 staff):** max 1 OFF per day — all OFFs done by Tuesday/Wednesday.
- **Large section (>6 staff, e.g. SERVERS):** max 2 OFF Sun–Tue, max 1 OFF Wed–Sat.

**Goal:** Full manning from Wednesday onward each week.

---

## Shift Consistency Rule

- Each staff member stays on the **same shift slot** (A, B, C, D, E, or F) for the entire week.
- **Reason:** Sleep balance and routine for the employee.

---

## Section Coverage

- Each section has a **min staff working per day** (total across all active shifts that day).
- Each section can have a **min per designation** (e.g. ≥1 Supervisor per day).
- Each section has a **max OFF per day** so that coverage is not stretched too thin.

Sections (e.g. MANAGERS, SERVERS, BAR, GRE, Housekeeping) are defined by the roster. Manager/Asst. Manager/Supervisor are often interchangeable for shift assignment purposes.

---

## What the Manager Provides

### One-time setup (per restaurant)

1. Restaurant name  
2. Week start day — Sunday (Middle East) or Monday (Western)  
3. OFF request deadline day (e.g. Friday)  
4. Schedule publish day (e.g. Saturday)  
5. Staff roster (upload or manual entry)

### Per schedule period

1. Schedule start date and end date  
2. Which shift slots are active this period (subset of A–F)  
3. For each section: min total staff per day  
4. For each section: min per designation per day (e.g. ≥1 Manager per day)  
5. For each section: max OFF per day  
6. Manual overrides for the period (staff × date → status code)  
7. Staff OFF requests (must be submitted by the deadline day)

---

*This file contains only scheduling rules and policy. For project context, tests, and technical details see `context.md`.*
