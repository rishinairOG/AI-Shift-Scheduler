"""Streamlit page: paste a schedule grid for AI sanity checking."""

import os
import streamlit as st


def render_schedule_check():
    st.header("Schedule Sanity Check")
    st.caption(
        "Paste an exported schedule grid (text or CSV) and the AI will flag "
        "likely rule violations — OFF distribution, shift consistency, coverage gaps, etc."
    )

    if not os.environ.get("OPENROUTER_API_KEY"):
        st.warning(
            "Set the **OPENROUTER_API_KEY** environment variable to enable this feature. "
            "Get a key at [openrouter.ai](https://openrouter.ai)."
        )
        return

    schedule_text = st.text_area(
        "Paste schedule grid here",
        height=250,
        placeholder=(
            "Staff       | Sun | Mon | Tue | Wed | Thu | Fri | Sat\n"
            "Alice (BAR) |  C  | OFF |  C  |  C  |  C  |  C  |  C\n"
            "Bob (BAR)   | OFF |  C  |  C  |  C  |  C  |  C  |  C\n"
            "..."
        ),
        key="sanity_input",
    )

    if st.button("Check for issues", type="primary", key="btn_sanity"):
        if not schedule_text.strip():
            st.warning("Paste a schedule first.")
            return

        with st.spinner("Analyzing schedule against rules… this may take a few seconds."):
            try:
                from src.rag.roster_sanity import check_schedule_sanity
                from src.rag.llm_client import friendly_error_message
                result = check_schedule_sanity(schedule_text)
            except Exception as e:
                result = friendly_error_message(e)

        st.subheader("Results")
        st.markdown(result)
