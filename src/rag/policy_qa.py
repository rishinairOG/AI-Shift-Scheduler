"""
RAG pipeline over docs/scheduling-rules.md.
Indexes the rules-only document and answers policy questions
grounded in that content (not context.md).
"""

import os
import pathlib

from langchain_openai import ChatOpenAI
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

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

_vectorstore_cache: FAISS | None = None


def _get_llm() -> ChatOpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.1,
        max_tokens=512,
    )


def _build_vectorstore() -> FAISS:
    global _vectorstore_cache
    if _vectorstore_cache is not None:
        return _vectorstore_cache

    text = RULES_PATH.read_text(encoding="utf-8")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n---\n", "\n## ", "\n### ", "\n\n", "\n", " "],
    )
    docs = splitter.create_documents([text], metadatas=[{"source": "scheduling-rules.md"}])

    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    _vectorstore_cache = FAISS.from_documents(docs, embeddings)
    return _vectorstore_cache


def _format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def answer_policy_question(question: str) -> str:
    """Retrieve relevant rule chunks and generate an answer via the LLM."""
    vectorstore = _build_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    llm = _get_llm()

    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | _QA_PROMPT
        | llm
        | StrOutputParser()
    )

    return chain.invoke(question)
