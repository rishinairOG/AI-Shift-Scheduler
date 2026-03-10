"""Streamlit page for policy Q&A (RAG over scheduling-rules.md)."""

import os
import streamlit as st


def render_policy_help():
    st.header("Scheduling Rules — Ask a Question")
    st.caption(
        "Ask anything about shift slots, status codes, OFF rules, coverage, "
        "or how the schedule works. Answers come from the scheduling-rules policy doc."
    )

    if not os.environ.get("OPENROUTER_API_KEY"):
        st.warning(
            "Set the **OPENROUTER_API_KEY** environment variable to enable AI-powered Q&A. "
            "You can get a key at [openrouter.ai](https://openrouter.ai)."
        )
        return

    if "policy_history" not in st.session_state:
        st.session_state["policy_history"] = []

    with st.container():
        for entry in st.session_state["policy_history"]:
            with st.chat_message("user"):
                st.write(entry["question"])
            with st.chat_message("assistant"):
                st.write(entry["answer"])

    question = st.chat_input("e.g. What's the OFF by Wednesday rule?")

    if question:
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Looking up rules..."):
                try:
                    from src.rag.policy_qa import answer_policy_question
                    answer = answer_policy_question(question)
                except Exception as e:
                    answer = f"Error: {e}"
                st.write(answer)

        st.session_state["policy_history"].append(
            {"question": question, "answer": answer}
        )
        st.rerun()

    if st.session_state["policy_history"]:
        if st.button("Clear history"):
            st.session_state["policy_history"] = []
            st.rerun()
