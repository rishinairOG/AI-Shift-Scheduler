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
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

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


def answer_policy_question(question: str) -> str:
    """Retrieve relevant rule chunks and generate an answer via the LLM."""
    vectorstore = _build_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    llm = _get_llm()

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": _QA_PROMPT},
        return_source_documents=True,
    )

    result = qa_chain.invoke({"query": question})
    return result["result"]
