import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.models.staff import Staff
from src.models.schedule import ScheduleConfig
from src.exporter.excel_exporter import export_schedule


def render_preview(
    staff_list: list[Staff],
    sections: dict[str, list[Staff]],
    config: ScheduleConfig,
    assignments: dict[tuple[str, date], str],
):
    """Render schedule preview with warnings and download button."""
    st.header("Schedule Preview")

    # Build date list
    dates = []
    current = config.start_date
    while current <= config.end_date:
        dates.append(current)
        current += timedelta(days=1)

    # Warnings
    warnings = _check_constraints(staff_list, sections, config, assignments, dates)
    if warnings:
        with st.expander(f"\u26a0\ufe0f {len(warnings)} Warning(s)", expanded=True):
            for w in warnings:
                st.warning(w)
    else:
        st.success("All constraints satisfied.")

    # OFF distribution summary
    with st.expander("OFF Distribution Summary", expanded=False):
        for sec_name, sec_staff in sections.items():
            off_counts = {}
            for d in dates:
                count = sum(1 for s in sec_staff if assignments.get((s.id, d)) == "OFF")
                if count:
                    off_counts[d.strftime("%a %d %b")] = count
            if off_counts:
                st.write(f"**{sec_name}:** " + ", ".join(f"{k}: {v}" for k, v in off_counts.items()))

    # Schedule grid per section
    for sec_name, sec_staff in sections.items():
        if not sec_staff:
            continue
        st.subheader(sec_name)
        rows = []
        for s in sec_staff:
            row = {"Name": s.name}
            for d in dates:
                code = assignments.get((s.id, d), "")
                row[d.strftime("%a %d")] = code
            rows.append(row)
        df = pd.DataFrame(rows).set_index("Name")

        def color_cell(val):
            if val == "OFF":
                return "background-color: #C0C0C0"
            if val in ("PH", "HP"):
                return "background-color: #FFFF99"
            if val in ("S", "HD", "HO", "TR", "V"):
                return "background-color: #FFD580"
            if val:
                return "background-color: #E8F5E9"
            return ""

        st.dataframe(df.style.applymap(color_cell), use_container_width=True)

    # AI summary for managers
    import os
    if os.environ.get("OPENROUTER_API_KEY"):
        with st.expander("AI summary for managers", expanded=False):
            if st.button("Generate summary", key="btn_ai_summary"):
                with st.spinner("Generating summary… this may take a few seconds."):
                    try:
                        from src.rag.schedule_summary import generate_schedule_summary
                        from src.rag.llm_client import friendly_error_message
                        summary = generate_schedule_summary(
                            staff_list, sections, config, assignments,
                        )
                    except Exception as e:
                        summary = friendly_error_message(e)
                st.markdown(summary)

    # Download button
    st.divider()
    excel_bytes = export_schedule(staff_list, sections, config, assignments)
    filename = f"{config.restaurant_name.replace(' ', '_')}_schedule_{config.start_date}_{config.end_date}.xlsx"
    st.download_button(
        label="Download Schedule (.xlsx)",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )


def _check_constraints(
    staff_list, sections, config, assignments, dates
) -> list[str]:
    warnings = []
    for sec_name, sec_staff in sections.items():
        min_total = config.section_min_per_day.get(sec_name, {}).get("total", 0)
        max_off = config.section_max_off_per_day.get(sec_name, 1)
        for d in dates:
            working = sum(
                1 for s in sec_staff
                if assignments.get((s.id, d), "") not in
                ("OFF", "PH", "HP", "S", "HD", "HO", "TR", "V", "")
            )
            off_count = sum(1 for s in sec_staff if assignments.get((s.id, d)) == "OFF")
            if min_total > 0 and working < min_total:
                warnings.append(
                    f"{d.strftime('%a %d %b')} \u2014 {sec_name}: only {working} working, minimum is {min_total}"
                )
            if off_count > max_off:
                warnings.append(
                    f"{d.strftime('%a %d %b')} \u2014 {sec_name}: {off_count} OFFs, maximum is {max_off}"
                )
    return warnings
