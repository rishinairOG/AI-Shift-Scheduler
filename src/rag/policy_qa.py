"""
RAG pipeline over docs/scheduling-rules.md.
Indexes the rules-only document and answers policy questions
grounded in that content (not context.md).
"""

import pathlib
import re
from dataclasses import dataclass, field

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.rag.llm_client import get_llm

RULES_PATH = pathlib.Path(__file__).resolve().parents[2] / "docs" / "scheduling-rules.md"

_QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "You are a scheduling-policy assistant for an F&B restaurant.\n"
        "Answer the question using ONLY the policy rules provided below.\n"
        "If the answer is not in the rules, say \"I don't have that information in the scheduling rules.\"\n"
        "Be concise and specific.\n\n"
        "--- RULES ---\n{context}\n--- END RULES ---\n\n"
        "Question: {question}\n"
        "Answer:"
    ),
)

@dataclass
class PolicyAnswer:
    answer: str
    sources: list[str] = field(default_factory=list)


_vectorstore_cache: FAISS | None = None


def _get_llm():
    return get_llm(temperature=0.1, max_tokens=512)


def _heading_for_chunk(chunk_text: str, full_text: str) -> str:
    """Find the nearest ## or ### heading above a chunk's first line."""
    idx = full_text.find(chunk_text[:60])
    if idx == -1:
        return "Scheduling Rules"
    preceding = full_text[:idx]
    matches = re.findall(r"^#{2,3}\s+(.+)$", preceding, re.MULTILINE)
    return matches[-1].strip() if matches else "Scheduling Rules"


def _build_vectorstore() -> FAISS:
    global _vectorstore_cache
    if _vectorstore_cache is not None:
        return _vectorstore_cache

    full_text = RULES_PATH.read_text(encoding="utf-8")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n---\n", "\n## ", "\n### ", "\n\n", "\n", " "],
    )
    raw_docs = splitter.create_documents(
        [full_text], metadatas=[{"source": "scheduling-rules.md"}]
    )

    for doc in raw_docs:
        doc.metadata["heading"] = _heading_for_chunk(doc.page_content, full_text)

    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    _vectorstore_cache = FAISS.from_documents(raw_docs, embeddings)
    return _vectorstore_cache


def _format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def answer_policy_question(question: str) -> str:
    """Retrieve relevant rule chunks and generate an answer via the LLM."""
    return answer_policy_question_with_sources(question).answer


def answer_policy_question_with_sources(question: str) -> PolicyAnswer:
    """Like answer_policy_question but also returns source section headings."""
    vectorstore = _build_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    llm = _get_llm()

    retrieved_docs = retriever.invoke(question)

    sources = list(dict.fromkeys(
        doc.metadata.get("heading", "Scheduling Rules") for doc in retrieved_docs
    ))

    chain = _QA_PROMPT | llm | StrOutputParser()
    answer = chain.invoke({
        "context": _format_docs(retrieved_docs),
        "question": question,
    })

    return PolicyAnswer(answer=answer, sources=sources)
