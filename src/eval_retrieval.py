"""Retrieval Quality Evaluator — measures Hit Rate@K, MRR, and Precision@K."""
import logging
from typing import List

from src.models import EvalItem, RetrievalScore, CategoryReport
from src.retriever import FirestoreRetriever


class RetrievalEvaluator:
    """Evaluates retrieval quality by comparing retrieved chunks to expected sources."""

    def __init__(self, retriever: FirestoreRetriever, logger: logging.Logger, k: int = 4):
        self._retriever = retriever
        self._logger = logger
        self._k = k

    def evaluate_item(self, item: EvalItem) -> RetrievalScore:
        """Score retrieval quality for a single eval item."""
        # Skip items with no expected sources (no-answer, ambiguous)
        if not item.expected_source_files and not item.expected_section_types:
            return RetrievalScore(
                question_id=item.id,
                hit=False,
                reciprocal_rank=0.0,
                precision=0.0,
            )

        raw_docs = self._retriever.as_langchain_retriever(k=self._k).invoke(item.question)
        self._logger.info("Q%d: retrieved %d docs for: %s", item.id, len(raw_docs), item.question[:60])

        hit = False
        first_relevant_rank = 0
        relevant_count = 0

        for rank, doc in enumerate(raw_docs, start=1):
            metadata = doc.metadata or {}
            source_file = metadata.get("source_file", "")
            section_type = metadata.get("section_type", "")

            is_relevant = False

            # Check source file match
            if item.expected_source_files:
                for expected in item.expected_source_files:
                    if expected in source_file or source_file in expected:
                        is_relevant = True
                        break

            # Check section type match (if no source files specified, use section types)
            if not item.expected_source_files and item.expected_section_types:
                if section_type in item.expected_section_types:
                    is_relevant = True

            # If both are specified, require section type match too
            if item.expected_source_files and item.expected_section_types and is_relevant:
                if section_type not in item.expected_section_types:
                    is_relevant = False

            if is_relevant:
                relevant_count += 1
                if not hit:
                    hit = True
                    first_relevant_rank = rank

        reciprocal_rank = (1.0 / first_relevant_rank) if first_relevant_rank > 0 else 0.0
        precision = relevant_count / len(raw_docs) if raw_docs else 0.0

        return RetrievalScore(
            question_id=item.id,
            hit=hit,
            reciprocal_rank=reciprocal_rank,
            precision=precision,
        )

    def evaluate_all(self, items: List[EvalItem]) -> CategoryReport:
        """Run retrieval evaluation on all items and produce a category report."""
        # Filter to items that have expected sources (skip no_answer, ambiguous)
        scorable = [item for item in items if item.expected_source_files or item.expected_section_types]
        self._logger.info("Evaluating retrieval quality on %d/%d items", len(scorable), len(items))

        scores: list[RetrievalScore] = []
        for item in scorable:
            score = self.evaluate_item(item)
            scores.append(score)

        if not scores:
            return CategoryReport(
                category="retrieval",
                score=0.0,
                status="fail",
                metrics={"hit_rate": 0.0, "mrr": 0.0, "precision": 0.0, "evaluated_count": 0},
                details=[],
            )

        hit_rate = sum(1 for s in scores if s.hit) / len(scores)
        mrr = sum(s.reciprocal_rank for s in scores) / len(scores)
        avg_precision = sum(s.precision for s in scores) / len(scores)

        # Overall score: weighted average (hit_rate most important)
        overall = (hit_rate * 50 + mrr * 30 + avg_precision * 20) * 100

        # Status thresholds
        if hit_rate >= 0.80 and mrr >= 0.60:
            status = "pass"
        elif hit_rate >= 0.60:
            status = "warn"
        else:
            status = "fail"

        self._logger.info(
            "Retrieval results — Hit Rate: %.2f | MRR: %.2f | Precision: %.2f | Status: %s",
            hit_rate, mrr, avg_precision, status,
        )

        return CategoryReport(
            category="retrieval",
            score=round(overall, 1),
            status=status,
            metrics={
                "hit_rate": round(hit_rate, 3),
                "mrr": round(mrr, 3),
                "precision": round(avg_precision, 3),
                "evaluated_count": len(scores),
            },
            details=[s.model_dump() for s in scores],
        )
