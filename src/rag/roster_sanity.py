"""
Schedule sanity checker: paste an exported schedule grid and have the LLM
flag likely mistakes versus scheduling rules.
"""

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.rag.llm_client import get_llm
from src.rag.policy_qa import _build_vectorstore, _format_docs


_SANITY_PROMPT = PromptTemplate(
    input_variables=["rules", "schedule"],
    template=(
        "You are a scheduling auditor for an F&B restaurant.\n"
        "Below are the scheduling rules, followed by a pasted schedule grid.\n\n"
        "--- RULES ---\n{rules}\n--- END RULES ---\n\n"
        "--- SCHEDULE ---\n{schedule}\n--- END SCHEDULE ---\n\n"
        "Instructions:\n"
        "1. Identify any rows or cells that likely violate the rules above.\n"
        "2. For each issue, cite which rule topic it relates to "
        "(e.g. 'OFF Distribution Rule', 'Shift Consistency', 'Section Coverage').\n"
        "3. If the data is ambiguous or incomplete, say so rather than guessing.\n"
        "4. Be concise — one bullet per issue.\n"
        "5. If everything looks correct, say 'No issues found.'\n\n"
        "Issues:"
    ),
)


def check_schedule_sanity(schedule_text: str) -> str:
    """
    Run the pasted schedule through RAG retrieval + LLM to flag rule violations.
    Returns a plain-text list of issues or 'No issues found.'
    """
    vectorstore = _build_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

    rule_docs = retriever.invoke(
        "OFF distribution coverage shift consistency manual overrides"
    )
    rules_context = _format_docs(rule_docs)

    llm = get_llm(temperature=0.1, max_tokens=1024)
    chain = _SANITY_PROMPT | llm | StrOutputParser()

    return chain.invoke({"rules": rules_context, "schedule": schedule_text})
