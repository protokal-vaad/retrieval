"""Answer Quality Evaluator — uses LLM-as-Judge for faithfulness, relevance, completeness."""
import logging
from typing import List

from evaluation.models import EvalItem, AnswerScore, CategoryReport
from evaluation.judge import JudgeAgent
from retrieval.retriever import FirestoreRetriever


class AnswerEvaluator:
    """Evaluates RAG answer quality using LLM-as-Judge scoring."""

    def __init__(self, judge: JudgeAgent, retriever: FirestoreRetriever, logger: logging.Logger):
        self._judge = judge
        self._retriever = retriever
        self._logger = logger

    def evaluate_item(self, item: EvalItem) -> AnswerScore:
        """Score answer quality for a single eval item."""
        # Retrieve context (same as RAGAgent does)
        raw_docs = self._retriever.retrieve(item.question, k=4)
        context = "\n\n".join(doc.page_content for doc in raw_docs)

        self._logger.info("Q%d: judging answer quality for: %s", item.id, item.question[:60])

        faithfulness = self._judge.score_faithfulness(context, item.answer)
        self._logger.info("  Faithfulness: %d/5", faithfulness.score)

        relevance = self._judge.score_relevance(item.question, item.answer)
        self._logger.info("  Relevance: %d/5", relevance.score)

        completeness = None
        if item.golden_answer:
            completeness = self._judge.score_completeness(item.golden_answer, item.answer)
            self._logger.info("  Completeness: %d/5 (missing: %s)", completeness.score, completeness.missing_facts)

        return AnswerScore(
            question_id=item.id,
            faithfulness=faithfulness,
            relevance=relevance,
            completeness=completeness,
        )

    def evaluate_all(self, items: List[EvalItem]) -> CategoryReport:
        """Run answer quality evaluation on all items."""
        # Skip no-answer items — they are evaluated in edge cases
        scorable = [item for item in items if item.category not in ("no_answer", "ambiguous") and item.answer]
        self._logger.info("Evaluating answer quality on %d/%d items", len(scorable), len(items))

        scores: list[AnswerScore] = []
        for item in scorable:
            score = self.evaluate_item(item)
            scores.append(score)

        if not scores:
            return CategoryReport(
                category="answer",
                score=0.0,
                status="fail",
                metrics={"faithfulness_avg": 0.0, "relevance_avg": 0.0, "completeness_avg": 0.0, "evaluated_count": 0},
                details=[],
            )

        faith_avg = sum(s.faithfulness.score for s in scores) / len(scores)
        rel_avg = sum(s.relevance.score for s in scores) / len(scores)

        completeness_scores = [s.completeness.score for s in scores if s.completeness]
        comp_avg = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0

        # Overall score: normalize to 0-100 (each metric is 1-5, so (avg-1)/4 * 100)
        faith_pct = (faith_avg - 1) / 4 * 100
        rel_pct = (rel_avg - 1) / 4 * 100
        comp_pct = (comp_avg - 1) / 4 * 100 if completeness_scores else faith_pct  # fallback

        overall = faith_pct * 0.4 + rel_pct * 0.4 + comp_pct * 0.2

        # Status thresholds
        if faith_avg >= 4.0 and rel_avg >= 4.0:
            status = "pass"
        elif faith_avg >= 3.0 and rel_avg >= 3.0:
            status = "warn"
        else:
            status = "fail"

        self._logger.info(
            "Answer results — Faithfulness: %.2f | Relevance: %.2f | Completeness: %.2f | Status: %s",
            faith_avg, rel_avg, comp_avg, status,
        )

        return CategoryReport(
            category="answer",
            score=round(overall, 1),
            status=status,
            metrics={
                "faithfulness_avg": round(faith_avg, 2),
                "relevance_avg": round(rel_avg, 2),
                "completeness_avg": round(comp_avg, 2),
                "completeness_count": len(completeness_scores),
                "evaluated_count": len(scores),
            },
            details=[s.model_dump() for s in scores],
        )
