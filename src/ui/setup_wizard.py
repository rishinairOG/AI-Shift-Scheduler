import streamlit as st
from config.defaults import (
    DEFAULT_WEEK_START, DEFAULT_OFF_DEADLINE, DEFAULT_PUBLISH_DAY,
    DAYS_SUN_START, DAYS_MON_START
)


def render_setup_wizard():
    """Render the restaurant setup wizard. Saves config to st.session_state."""
    st.header("Restaurant Setup")
    st.caption("Configure your restaurant once. These settings are saved for all future schedules.")

    with st.form("setup_form"):
        restaurant_name = st.text_input(
            "Restaurant Name",
            value=st.session_state.get("restaurant_name", ""),
            placeholder="e.g. White Robata KSA"
        )

        week_start = st.radio(
            "Week Starts On",
            options=["SUN", "MON"],
            index=0 if st.session_state.get("week_start_day", DEFAULT_WEEK_START) == "SUN" else 1,
            horizontal=True,
            help="Middle East: Sunday | Western: Monday"
        )

        all_days = DAYS_SUN_START if week_start == "SUN" else DAYS_MON_START

        off_deadline = st.selectbox(
            "Staff OFF Request Deadline",
            options=all_days,
            index=all_days.index(st.session_state.get("off_request_deadline", DEFAULT_OFF_DEADLINE))
            if st.session_state.get("off_request_deadline", DEFAULT_OFF_DEADLINE) in all_days else 0,
            help="Last day staff can submit OFF requests for the following week"
        )

        publish_day = st.selectbox(
            "Schedule Publish Day",
            options=all_days,
            index=all_days.index(st.session_state.get("publish_day", DEFAULT_PUBLISH_DAY))
            if st.session_state.get("publish_day", DEFAULT_PUBLISH_DAY) in all_days else 0,
            help="Day the new schedule is generated and published to staff"
        )

        submitted = st.form_submit_button("Save Setup", type="primary")

    if submitted:
        if not restaurant_name.strip():
            st.error("Please enter a restaurant name.")
            return False

        st.session_state["restaurant_name"] = restaurant_name.strip()
        st.session_state["week_start_day"] = week_start
        st.session_state["off_request_deadline"] = off_deadline
        st.session_state["publish_day"] = publish_day
        st.success(f"Setup saved for **{restaurant_name}**")
        return True

    return bool(st.session_state.get("restaurant_name"))
