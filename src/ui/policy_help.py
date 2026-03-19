"""Streamlit page for policy Q&A (RAG over scheduling-rules.md)."""

import os
import streamlit as st


_EXAMPLE_QUESTIONS = [
    "What is the OFF by Wednesday rule?",
    "Which status codes can a manager set manually?",
    "Does a staff member keep the same shift all week?",
    "How is section coverage determined?",
    "What happens if I mark someone as PH — does the optimizer change it?",
    "What's the difference between OFF requests and manual overrides?",
]


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

    with st.expander("How to ask — example questions", expanded=False):
        for q in _EXAMPLE_QUESTIONS:
            st.markdown(f"- *{q}*")

    if "policy_history" not in st.session_state:
        st.session_state["policy_history"] = []

    with st.container():
        for entry in st.session_state["policy_history"]:
            with st.chat_message("user"):
                st.write(entry["question"])
            with st.chat_message("assistant"):
                st.write(entry["answer"])
                if entry.get("sources"):
                    with st.expander("Sources used"):
                        for src in entry["sources"]:
                            st.markdown(f"- {src}")

    question = st.chat_input("e.g. What's the OFF by Wednesday rule?")

    if question:
        with st.chat_message("user"):
            st.write(question)

        sources = []
        with st.chat_message("assistant"):
            with st.spinner("Looking up rules… this may take a few seconds."):
                try:
                    from src.rag.policy_qa import answer_policy_question_with_sources
                    from src.rag.llm_client import friendly_error_message, log_qa_interaction
                    result = answer_policy_question_with_sources(question)
                    answer = result.answer
                    sources = result.sources
                    log_qa_interaction(question, answer, extra={"sources": sources})
                except Exception as e:
                    answer = friendly_error_message(e)
                st.write(answer)
                if sources:
                    with st.expander("Sources used"):
                        for src in sources:
                            st.markdown(f"- {src}")

        st.session_state["policy_history"].append(
            {"question": question, "answer": answer, "sources": sources}
        )
        st.rerun()

    if st.session_state["policy_history"]:
        if st.button("Clear history"):
            st.session_state["policy_history"] = []
            st.rerun()
