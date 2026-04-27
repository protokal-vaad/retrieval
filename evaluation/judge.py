"""LLM-as-Judge — scores RAG answers for faithfulness, relevance, and completeness."""
import logging

from pydantic_ai import Agent

from evaluation.models import JudgeScore, CompletenessScore
from retrieval.request_guard import RequestGuard


_FAITHFULNESS_PROMPT = """You are an evaluation judge. Score the FAITHFULNESS of an answer.

Faithfulness means the answer uses ONLY information from the provided context.
- Score 5: every claim in the answer is directly supported by the context.
- Score 4: almost all claims are supported, minor unsupported phrasing.
- Score 3: most claims are supported but some are inferred or ambiguous.
- Score 2: significant claims are not in the context.
- Score 1: the answer invents facts not present in the context.

Respond in JSON with "score" (1-5) and "reasoning" (brief explanation in Hebrew)."""


_RELEVANCE_PROMPT = """You are an evaluation judge. Score the RELEVANCE of an answer.

Relevance means the answer directly addresses the question asked.
- Score 5: the answer fully and directly addresses the question.
- Score 4: the answer mostly addresses the question with minor tangents.
- Score 3: the answer partially addresses the question.
- Score 2: the answer barely addresses the question.
- Score 1: the answer is completely off-topic.

Respond in JSON with "score" (1-5) and "reasoning" (brief explanation in Hebrew)."""


_COMPLETENESS_PROMPT = """You are an evaluation judge. Score the COMPLETENESS of an answer by comparing it to a reference answer.

Completeness means the answer covers all key facts from the reference.
- Score 5: all key facts from the reference are present in the answer.
- Score 4: most key facts are present, one minor fact missing.
- Score 3: several facts are missing but the core is there.
- Score 2: major facts are missing.
- Score 1: the answer is missing most of the reference content.

Respond in JSON with "score" (1-5) and "missing_facts" (list of key facts from the reference that are missing in the answer, in Hebrew)."""


class JudgeAgent:
    """Pydantic AI agent that scores RAG answers using Gemini as judge."""

    def __init__(self, model_name: str, request_guard: RequestGuard, logger: logging.Logger):
        self._model_name = model_name
        self._request_guard = request_guard
        self._logger = logger
        self._faithfulness_agent: Agent = None
        self._relevance_agent: Agent = None
        self._completeness_agent: Agent = None

    def setup(self) -> None:
        """Initialize the three judge agents."""
        self._logger.info("Initializing Judge agents with model: %s", self._model_name)

        self._faithfulness_agent = Agent(
            f"google-vertex:{self._model_name}",
            system_prompt=_FAITHFULNESS_PROMPT,
            output_type=JudgeScore,
        )
        self._relevance_agent = Agent(
            f"google-vertex:{self._model_name}",
            system_prompt=_RELEVANCE_PROMPT,
            output_type=JudgeScore,
        )
        self._completeness_agent = Agent(
            f"google-vertex:{self._model_name}",
            system_prompt=_COMPLETENESS_PROMPT,
            output_type=CompletenessScore,
        )
        self._logger.info("Judge agents ready.")

    def score_faithfulness(self, context: str, answer: str) -> JudgeScore:
        """Score how faithful the answer is to the provided context."""
        prompt = f"Context:\n{context}\n\nAnswer:\n{answer}"
        result = self._request_guard.run(
            "faithfulness judge",
            lambda: self._faithfulness_agent.run_sync(prompt),
        )
        return result.output

    def score_relevance(self, question: str, answer: str) -> JudgeScore:
        """Score how relevant the answer is to the question."""
        prompt = f"Question:\n{question}\n\nAnswer:\n{answer}"
        result = self._request_guard.run(
            "relevance judge",
            lambda: self._relevance_agent.run_sync(prompt),
        )
        return result.output

    def score_completeness(self, golden_answer: str, rag_answer: str) -> CompletenessScore:
        """Score answer completeness against a golden reference answer."""
        prompt = f"Reference Answer:\n{golden_answer}\n\nRAG Answer:\n{rag_answer}"
        result = self._request_guard.run(
            "completeness judge",
            lambda: self._completeness_agent.run_sync(prompt),
        )
        return result.output
