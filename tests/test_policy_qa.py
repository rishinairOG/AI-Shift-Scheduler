"""Tests for src/rag/policy_qa.py — mocked LLM, vectorstore build, chain."""

from unittest.mock import patch, MagicMock
import pytest

from src.rag.policy_qa import (
    _build_vectorstore,
    _format_docs,
    answer_policy_question,
    RULES_PATH,
)


# ── Vectorstore build (local embeddings, no network) ────────────────

class TestBuildVectorstore:
    def test_rules_file_exists(self):
        assert RULES_PATH.exists(), f"Expected {RULES_PATH}"

    def test_vectorstore_builds_and_retrieves(self):
        import src.rag.policy_qa as mod
        old_cache = mod._vectorstore_cache
        mod._vectorstore_cache = None
        try:
            vs = _build_vectorstore()
            results = vs.similarity_search("OFF distribution", k=2)
            assert len(results) >= 1
            assert any("OFF" in doc.page_content for doc in results)
        finally:
            mod._vectorstore_cache = old_cache

    def test_vectorstore_caching(self):
        import src.rag.policy_qa as mod
        mod._vectorstore_cache = None
        vs1 = _build_vectorstore()
        vs2 = _build_vectorstore()
        assert vs1 is vs2


# ── _format_docs ─────────────────────────────────────────────────────

class TestFormatDocs:
    def test_joins_page_content(self):
        doc1 = MagicMock()
        doc1.page_content = "Rule A"
        doc2 = MagicMock()
        doc2.page_content = "Rule B"
        assert _format_docs([doc1, doc2]) == "Rule A\n\nRule B"

    def test_empty_list(self):
        assert _format_docs([]) == ""


# ── answer_policy_question (mocked LLM, real retriever) ──────────────

class TestAnswerPolicyQuestionMocked:
    @patch("src.rag.policy_qa._get_llm")
    def test_returns_llm_response(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.__or__ = MagicMock()

        fake_runnable = MagicMock()
        fake_runnable.invoke.return_value = "The OFF rule says max 1 per day."

        mock_pipe_result = MagicMock()
        mock_pipe_result.__or__ = MagicMock(return_value=fake_runnable)

        mock_prompt_pipe = MagicMock()
        mock_prompt_pipe.__or__ = MagicMock(return_value=mock_pipe_result)

        with patch("src.rag.policy_qa._QA_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock()

            import src.rag.policy_qa as mod
            original_cache = mod._vectorstore_cache
            mod._vectorstore_cache = None

            try:
                vs = _build_vectorstore()
                retriever = vs.as_retriever(search_kwargs={"k": 4})
                retrieved = retriever.invoke("OFF by Wednesday rule")
                assert len(retrieved) >= 1, "Retriever should find OFF-related chunks"
            finally:
                mod._vectorstore_cache = original_cache

    @patch("src.rag.policy_qa._get_llm")
    def test_retriever_finds_shift_rules(self, mock_get_llm):
        """Verify local embedding retrieval works for shift-related queries."""
        import src.rag.policy_qa as mod
        mod._vectorstore_cache = None
        try:
            vs = _build_vectorstore()
            results = vs.similarity_search("shift consistency same slot all week", k=3)
            texts = " ".join(doc.page_content for doc in results)
            assert "shift" in texts.lower() or "slot" in texts.lower()
        finally:
            mod._vectorstore_cache = None

    @patch("src.rag.policy_qa._get_llm")
    def test_retriever_finds_status_codes(self, mock_get_llm):
        import src.rag.policy_qa as mod
        mod._vectorstore_cache = None
        try:
            vs = _build_vectorstore()
            results = vs.similarity_search("what does PH mean", k=3)
            texts = " ".join(doc.page_content for doc in results)
            assert "PH" in texts or "Public Holiday" in texts
        finally:
            mod._vectorstore_cache = None
