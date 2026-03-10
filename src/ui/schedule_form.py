import streamlit as st
import pandas as pd
from datetime import date, timedelta
from config.defaults import STANDARD_SHIFT_SLOTS, MANUAL_STATUS_CODES
from src.models.schedule import ScheduleConfig


def render_schedule_form(staff_list, sections) -> ScheduleConfig | None:
    """Render per-schedule configuration form. Returns ScheduleConfig or None."""
    st.header("Schedule Configuration")

    # Date range
    st.subheader("1. Schedule Period")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today())
    with col2:
        end_date = st.date_input("End Date", value=date.today() + timedelta(days=6))

    if end_date < start_date:
        st.error("End date must be after start date.")
        return None

    # Active shift slots
    st.subheader("2. Active Shift Slots")
    st.caption("Select which shifts run at your restaurant this period.")
    slot_options = {s["code"]: f"{s['code']} \u2014 {s['label']}" for s in STANDARD_SHIFT_SLOTS}
    selected_slots = st.multiselect(
        "Active Shift Slots",
        options=list(slot_options.keys()),
        format_func=lambda x: slot_options[x],
        default=st.session_state.get("active_slots", ["C", "D"]),
    )
    if not selected_slots:
        st.warning("Select at least one shift slot.")
        return None
    st.session_state["active_slots"] = selected_slots

    # Section constraints
    st.subheader("3. Coverage Constraints (per section, per day)")
    section_min_per_day = {}
    section_max_off_per_day = {}

    for sec_name, sec_staff in sections.items():
        sec_size = len(sec_staff)
        if sec_size == 0:
            continue
        with st.expander(f"{sec_name} ({sec_size} staff)", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                min_total = st.number_input(
                    f"Min staff working per day",
                    min_value=0, max_value=sec_size,
                    value=max(1, sec_size - 2),
                    key=f"min_total_{sec_name}"
                )
            with col2:
                max_off = st.number_input(
                    f"Max OFF per day",
                    min_value=1, max_value=sec_size,
                    value=2 if sec_size > 6 else 1,
                    key=f"max_off_{sec_name}"
                )
            section_min_per_day[sec_name] = {"total": int(min_total)}
            section_max_off_per_day[sec_name] = int(max_off)

    # Manual overrides
    st.subheader("4. Manual Overrides (PH, Sick Leave, Vacation, etc.)")
    st.caption("Enter exceptions \u2014 these override AI assignments.")
    override_data = st.data_editor(
        pd.DataFrame(columns=["Staff Name", "Date (YYYY-MM-DD)", "Status Code"]),
        num_rows="dynamic",
        use_container_width=True,
        key="override_editor"
    )

    manual_overrides = {}
    if override_data is not None and not override_data.empty:
        for _, row in override_data.iterrows():
            name = str(row.get("Staff Name", "")).strip()
            dstr = str(row.get("Date (YYYY-MM-DD)", "")).strip()
            code = str(row.get("Status Code", "")).strip().upper()
            if name and dstr and code in MANUAL_STATUS_CODES:
                matched = [s for s in staff_list if s.name.lower() == name.lower()]
                if matched:
                    manual_overrides[(matched[0].id, dstr)] = code

    # OFF requests
    st.subheader("5. Staff OFF Requests")
    st.caption("Staff who have requested specific days off this week.")
    off_req_data = st.data_editor(
        pd.DataFrame(columns=["Staff Name", "Requested OFF Date (YYYY-MM-DD)"]),
        num_rows="dynamic",
        use_container_width=True,
        key="off_req_editor"
    )

    off_requests = {}
    if off_req_data is not None and not off_req_data.empty:
        for _, row in off_req_data.iterrows():
            name = str(row.get("Staff Name", "")).strip()
            dstr = str(row.get("Requested OFF Date (YYYY-MM-DD)", "")).strip()
            if name and dstr:
                matched = [s for s in staff_list if s.name.lower() == name.lower()]
                if matched:
                    sid = matched[0].id
                    off_requests.setdefault(sid, []).append(dstr)

    # Generate button
    if st.button("Generate Schedule", type="primary", use_container_width=True):
        return ScheduleConfig(
            restaurant_name=st.session_state.get("restaurant_name", "Restaurant"),
            week_start_day=st.session_state.get("week_start_day", "SUN"),
            off_request_deadline=st.session_state.get("off_request_deadline", "FRI"),
            publish_day=st.session_state.get("publish_day", "SAT"),
            start_date=start_date,
            end_date=end_date,
            active_shift_slots=selected_slots,
            section_min_per_day=section_min_per_day,
            section_max_off_per_day=section_max_off_per_day,
            manual_overrides=manual_overrides,
            off_requests=off_requests,
        )

    return None
