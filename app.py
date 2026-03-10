import streamlit as st
from src.parser.roster_parser import parse_roster
from src.solver.optimizer import optimize_schedule
from src.ui.setup_wizard import render_setup_wizard
from src.ui.schedule_form import render_schedule_form
from src.ui.preview import render_preview
from src.ui.policy_help import render_policy_help
import tempfile
import os

st.set_page_config(
    page_title="AI Shift Scheduler",
    page_icon="\U0001f4c5",
    layout="wide",
)

st.title("AI Shift Scheduler")
st.caption("Automated duty schedule generation for F&B operations")

# Sidebar navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Go to",
        options=["1. Setup", "2. Upload Roster", "3. Generate Schedule", "4. Policy Help"],
        index=0,
    )
    st.divider()
    if st.session_state.get("restaurant_name"):
        st.success(f"Restaurant: **{st.session_state['restaurant_name']}**")
    if st.session_state.get("staff_list"):
        st.info(f"Staff loaded: **{len(st.session_state['staff_list'])}**")

# Page routing
if page == "1. Setup":
    render_setup_wizard()

elif page == "2. Upload Roster":
    st.header("Upload Staff Roster")
    st.caption("Upload your existing Excel roster file. The system will extract staff and sections automatically.")

    uploaded = st.file_uploader(
        "Upload Roster (.xlsx)",
        type=["xlsx"],
        help="Use your existing duty roster format"
    )

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        try:
            staff_list, sections = parse_roster(tmp_path)
            os.unlink(tmp_path)

            if not staff_list:
                st.error("No staff found. Check that your file matches the expected format.")
            else:
                st.session_state["staff_list"] = staff_list
                st.session_state["sections"] = sections
                st.success(f"Loaded **{len(staff_list)} staff** across **{len(sections)} sections**")

                for sec_name, sec_staff in sections.items():
                    with st.expander(f"{sec_name} ({len(sec_staff)} staff)"):
                        for s in sec_staff:
                            st.text(f"  {s.name} \u2014 {s.designation}")
        except Exception as e:
            st.error(f"Failed to parse roster: {e}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    st.divider()
    st.subheader("Or add staff manually")
    if st.button("Start with empty roster"):
        st.session_state["staff_list"] = []
        st.session_state["sections"] = {}
        st.info("You can add staff via the schedule form.")

elif page == "3. Generate Schedule":
    staff_list = st.session_state.get("staff_list")
    sections = st.session_state.get("sections")

    if not staff_list:
        st.warning("Please upload a roster first (Step 2).")
    elif not st.session_state.get("restaurant_name"):
        st.warning("Please complete setup first (Step 1).")
    else:
        config = render_schedule_form(staff_list, sections)

        if config is not None:
            with st.spinner("Optimizing schedule... this may take up to 30 seconds."):
                assignments = optimize_schedule(staff_list, sections, config)

            st.session_state["last_assignments"] = assignments
            st.session_state["last_config"] = config

        if st.session_state.get("last_assignments") and st.session_state.get("last_config"):
            render_preview(
                staff_list,
                sections,
                st.session_state["last_config"],
                st.session_state["last_assignments"],
            )

elif page == "4. Policy Help":
    render_policy_help()
