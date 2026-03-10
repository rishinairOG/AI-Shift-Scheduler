"""
Constraint-based weekly shift optimizer using OR-Tools CP-SAT.

For each week in the schedule date range:
- Each staff gets exactly 1 OFF day
- Staff stays on the same shift slot all week
- Max OFF per day per section is respected
- Min working staff per day per section is respected
- Manual overrides lock cells
- OFF requests are honored as soft constraints
"""
from datetime import date, timedelta
from ortools.sat.python import cp_model
from src.models.staff import Staff
from src.models.schedule import ScheduleConfig


def get_week_dates(start_date: date, end_date: date) -> list[list[date]]:
    """Split date range into 7-day weeks."""
    weeks = []
    current = start_date
    while current <= end_date:
        week_end = min(current + timedelta(days=6), end_date)
        week = [current + timedelta(days=i) for i in range((week_end - current).days + 1)]
        weeks.append(week)
        current = week_end + timedelta(days=1)
    return weeks


def optimize_week(
    staff_list: list[Staff],
    sections: dict[str, list[Staff]],
    config: ScheduleConfig,
    week_dates: list[date],
) -> dict[tuple[str, date], str]:
    """
    Optimize assignments for a single week.
    Returns {(staff_id, date): shift_code | "OFF" | status_code}
    """
    model = cp_model.CpModel()
    n_staff = len(staff_list)
    n_days = len(week_dates)
    n_slots = len(config.active_shift_slots)

    if n_staff == 0 or n_slots == 0:
        return {}

    staff_index = {s.id: i for i, s in enumerate(staff_list)}
    date_str_index = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(week_dates)}

    # Collect manual overrides for this week
    week_overrides: dict[tuple[int, int], str] = {}
    for (sid, dstr), code in config.manual_overrides.items():
        if sid in staff_index and dstr in date_str_index:
            week_overrides[(staff_index[sid], date_str_index[dstr])] = code

    # Variables: off_day[i] = day index (0..n_days-1) when staff i is off
    off_day = [model.new_int_var(0, n_days - 1, f"off_{i}") for i in range(n_staff)]

    # Variables: shift_var[i] = shift slot index (0..n_slots-1) for staff i this week
    shift_var = [model.new_int_var(0, n_slots - 1, f"shift_{i}") for i in range(n_staff)]

    # Bool vars: is_off[i][d] = True if staff i is off on day d
    is_off = []
    for i in range(n_staff):
        row = []
        for d in range(n_days):
            b = model.new_bool_var(f"is_off_{i}_{d}")
            model.add(off_day[i] == d).only_enforce_if(b)
            model.add(off_day[i] != d).only_enforce_if(~b)
            row.append(b)
        is_off.append(row)

    # Bool vars: on_shift[i][k][d] = True if staff i works shift k on day d
    on_shift = []
    for i in range(n_staff):
        staff_shifts = []
        for k in range(n_slots):
            slot_days = []
            for d in range(n_days):
                b = model.new_bool_var(f"on_shift_{i}_{k}_{d}")
                # on_shift[i][k][d] = (shift_var[i] == k) AND (not is_off[i][d]) AND (no override on (i,d))
                if (i, d) in week_overrides:
                    model.add(b == 0)
                else:
                    shift_matches = model.new_bool_var(f"shift_matches_{i}_{k}_{d}")
                    model.add(shift_var[i] == k).only_enforce_if(shift_matches)
                    model.add(shift_var[i] != k).only_enforce_if(~shift_matches)
                    model.add_bool_and([shift_matches, ~is_off[i][d]]).only_enforce_if(b)
                    model.add_bool_or([~shift_matches, is_off[i][d]]).only_enforce_if(~b)
                slot_days.append(b)
            staff_shifts.append(slot_days)
        on_shift.append(staff_shifts)

    # Constraint: fixed off day
    day_name_to_idx = {}
    day_names_all = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for j, d in enumerate(week_dates):
        day_name_to_idx[day_names_all[d.weekday()]] = j

    for i, s in enumerate(staff_list):
        if s.fixed_off_day and s.fixed_off_day in day_name_to_idx:
            model.add(off_day[i] == day_name_to_idx[s.fixed_off_day])

    # Constraint: max off per day per section
    for sec_name, sec_staff in sections.items():
        max_off = config.section_max_off_per_day.get(sec_name, 1)
        for d in range(n_days):
            off_in_section = [is_off[staff_index[s.id]][d] for s in sec_staff if s.id in staff_index]
            if off_in_section:
                model.add(sum(off_in_section) <= max_off)

    # Constraint: min working staff per day per section
    for sec_name, sec_staff in sections.items():
        min_rules = config.section_min_per_day.get(sec_name, {})
        min_total = min_rules.get("total", 0)
        for d in range(n_days):
            working = []
            for s in sec_staff:
                if s.id not in staff_index:
                    continue
                i = staff_index[s.id]
                if (i, d) in week_overrides:
                    continue  # override — don't count as working
                working.append(~is_off[i][d])
            if working and min_total > 0:
                model.add(sum(working) >= min(min_total, len(working)))

        # Designation-level minimums
        for desig, min_count in min_rules.items():
            if desig == "total":
                continue
            desig_staff = [s for s in sec_staff if s.designation == desig]
            for d in range(n_days):
                working = []
                for s in desig_staff:
                    if s.id not in staff_index:
                        continue
                    i = staff_index[s.id]
                    if (i, d) in week_overrides:
                        continue
                    working.append(~is_off[i][d])
                if working and min_count > 0:
                    model.add(sum(working) >= min(min_count, len(working)))

    # Soft: honor OFF requests
    request_honors = []
    for i, s in enumerate(staff_list):
        if s.id in config.off_requests:
            for dstr in config.off_requests[s.id]:
                if dstr in date_str_index:
                    d = date_str_index[dstr]
                    request_honors.append(is_off[i][d])

    # Soft: front-load OFFs (prefer early days in week)
    early_off_bonus = []
    for i in range(n_staff):
        for d in range(min(3, n_days)):  # Sun, Mon, Tue
            early_off_bonus.append(is_off[i][d])

    # Objective: maximize honored requests + small bonus for early-week OFFs
    model.maximize(sum(request_honors) * 10 + sum(early_off_bonus))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.solve(model)

    result: dict[tuple[str, date], str] = {}

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i, s in enumerate(staff_list):
            off_d = solver.value(off_day[i])
            slot_k = solver.value(shift_var[i])
            shift_code = config.active_shift_slots[slot_k]
            for d_idx, d in enumerate(week_dates):
                key = (s.id, d)
                dstr = d.strftime("%Y-%m-%d")
                if (i, d_idx) in week_overrides:
                    result[key] = week_overrides[(i, d_idx)]
                elif d_idx == off_d:
                    result[key] = "OFF"
                else:
                    result[key] = shift_code
    else:
        # Fallback: assign shift codes with simple round-robin OFF distribution
        result = _fallback_assign(staff_list, sections, config, week_dates, week_overrides)

    return result


def _fallback_assign(
    staff_list: list[Staff],
    sections: dict[str, list[Staff]],
    config: ScheduleConfig,
    week_dates: list[date],
    week_overrides: dict[tuple[int, int], str],
) -> dict[tuple[str, date], str]:
    """Simple fallback when solver is infeasible: round-robin OFF assignment."""
    result = {}
    staff_index = {s.id: i for i, s in enumerate(staff_list)}
    n_slots = len(config.active_shift_slots)

    for sec_name, sec_staff in sections.items():
        for s_pos, s in enumerate(sec_staff):
            if s.id not in staff_index:
                continue
            i = staff_index[s.id]
            off_day_idx = s_pos % len(week_dates)
            shift_code = config.active_shift_slots[s_pos % n_slots]
            for d_idx, d in enumerate(week_dates):
                key = (s.id, d)
                if (i, d_idx) in week_overrides:
                    result[key] = week_overrides[(i, d_idx)]
                elif d_idx == off_day_idx:
                    result[key] = "OFF"
                else:
                    result[key] = shift_code
    return result


def optimize_schedule(
    staff_list: list[Staff],
    sections: dict[str, list[Staff]],
    config: ScheduleConfig,
) -> dict[tuple[str, date], str]:
    """
    Optimize full schedule across all weeks in date range.
    Returns complete assignment for every (staff_id, date) pair.
    """
    weeks = get_week_dates(config.start_date, config.end_date)
    full_result = {}
    for week_dates in weeks:
        week_result = optimize_week(staff_list, sections, config, week_dates)
        full_result.update(week_result)
    return full_result
