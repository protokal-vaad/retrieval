"""Edge Case Evaluator â€” tests no-answer, cross-protocol, specificity, and ambiguous handling."""
import logging
import re
from typing import List

from src.agent import RAGAgent
from src.models import CategoryReport, EdgeCaseResult, EvalItem
from src.retriever import FirestoreRetriever


_REFUSAL_PHRASES = [
    "××™×Ÿ ×œ×™ ×ž×¡×¤×™×§ ×ž×™×“×¢",
    "××™×Ÿ ×ž×™×“×¢",
    "×œ× × ×ž×¦×",
    "×œ× × ×“×•×Ÿ",
    "×œ× ×¢×œ×”",
    "I don't know",
    "I don't have enough information",
    "××™×Ÿ ×‘×¤×¨×•×˜×•×§×•×œ×™×",
    "×œ× ×ž×•×¤×™×¢",
    "××™×Ÿ ×”×ª×™×™×—×¡×•×ª",
    "×œ× × ×™×ª×Ÿ ×œ×¢× ×•×ª",
    "×”×ž×™×“×¢ ××™× ×•",
    "××™×Ÿ × ×ª×•× ×™×",
]

_REFUSAL_RE = re.compile("|".join(re.escape(p) for p in _REFUSAL_PHRASES), re.IGNORECASE)


class EdgeCaseEvaluator:
    """Evaluates how the RAG system handles edge cases."""

    def __init__(self, retriever: FirestoreRetriever, agent: RAGAgent, logger: logging.Logger):
        self._retriever = retriever
        self._agent = agent
        self._logger = logger

    @staticmethod
    def _extract_chunk_metadata(raw_metadata: dict | None) -> dict:
        """Normalize vector-store metadata into the chunk metadata shape used by evals."""
        if not raw_metadata:
            return {}
        nested = raw_metadata.get("metadata")
        if isinstance(nested, dict):
            return nested
        return raw_metadata

    @staticmethod
    def _count_number_tokens(text: str) -> int:
        """Count concrete numeric tokens in an answer."""
        return len(re.findall(r"[\d,./%-]+", text))

    def _eval_no_answer(self, item: EvalItem) -> EdgeCaseResult:
        """Check if the system correctly refuses to answer when there is no relevant info."""
        result = self._agent.run(item.question)
        has_refusal = bool(_REFUSAL_RE.search(result.answer))
        answer_length = len(result.answer)
        number_count = self._count_number_tokens(result.answer)
        passed = has_refusal and answer_length <= 320 and number_count <= 4

        return EdgeCaseResult(
            question_id=item.id,
            category="no_answer",
            passed=passed,
            detail=(
                "Correctly refused"
                if passed
                else f"Refusal: {'yes' if has_refusal else 'no'} | Length: {answer_length} | Numbers: {number_count}"
            ),
        )

    def _eval_cross_protocol(self, item: EvalItem) -> EdgeCaseResult:
        """Check if retrieval spans multiple source files and the answer shows actual synthesis."""
        raw_docs = self._retriever.as_langchain_retriever(k=4).invoke(item.question)
        source_files = {
            self._extract_chunk_metadata(doc.metadata).get("source_file", "")
            for doc in raw_docs
            if doc.metadata
        }
        source_files.discard("")

        result = self._agent.run(item.question)
        multi_source = len(source_files) >= 2
        has_refusal = bool(_REFUSAL_RE.search(result.answer))
        answer_length = len(result.answer)
        passed = multi_source and not has_refusal and answer_length >= 80

        return EdgeCaseResult(
            question_id=item.id,
            category="cross_protocol",
            passed=passed,
            detail=(
                f"Retrieved from {len(source_files)} source(s): {', '.join(sorted(source_files)[:3])} | "
                f"Refusal: {'yes' if has_refusal else 'no'} | Length: {answer_length}"
            ),
        )

    def _eval_specificity(self, item: EvalItem) -> EdgeCaseResult:
        """Check if the answer contains the exact expected value from golden_answer."""
        result = self._agent.run(item.question)

        if not item.golden_answer:
            return EdgeCaseResult(
                question_id=item.id,
                category="specificity",
                passed=False,
                detail="No golden_answer provided for specificity check",
            )

        golden_numbers = re.findall(r"[\d,]+", item.golden_answer)
        matched_numbers = sum(1 for n in golden_numbers if n in result.answer)

        golden_words = set(re.findall(r"[\u0590-\u05FF]+", item.golden_answer))
        answer_words = set(re.findall(r"[\u0590-\u05FF]+", result.answer))
        word_overlap = len(golden_words & answer_words) / len(golden_words) if golden_words else 0

        passed = (golden_numbers and matched_numbers == len(golden_numbers)) or word_overlap >= 0.6

        return EdgeCaseResult(
            question_id=item.id,
            category="specificity",
            passed=passed,
            detail=f"Numbers matched: {matched_numbers}/{len(golden_numbers)} | Word overlap: {word_overlap:.0%}",
        )

    def _eval_ambiguous(self, item: EvalItem) -> EdgeCaseResult:
        """Check that the system handles vague questions gracefully."""
        result = self._agent.run(item.question)
        has_refusal_or_caveat = bool(_REFUSAL_RE.search(result.answer))
        answer_length = len(result.answer)
        number_count = self._count_number_tokens(result.answer)

        if has_refusal_or_caveat:
            passed = True
            detail = "Handled gracefully â€” gave caveated or refusal response"
        elif answer_length <= 280 and number_count <= 2 and result.source_documents:
            passed = True
            detail = f"Gave bounded contextual answer ({answer_length} chars, {number_count} numeric token(s))"
        else:
            passed = False
            detail = (
                f"Too specific for ambiguous query ({answer_length} chars, {number_count} numeric token(s), "
                f"{len(result.source_documents)} sources)"
            )

        return EdgeCaseResult(
            question_id=item.id,
            category="ambiguous",
            passed=passed,
            detail=detail,
        )

    def evaluate_item(self, item: EvalItem) -> EdgeCaseResult:
        """Route to the correct evaluator based on category."""
        self._logger.info("Q%d: evaluating edge case (%s): %s", item.id, item.category, item.question[:60])

        evaluators = {
            "no_answer": self._eval_no_answer,
            "cross_protocol": self._eval_cross_protocol,
            "specificity": self._eval_specificity,
            "ambiguous": self._eval_ambiguous,
        }

        evaluator = evaluators.get(item.category)
        if not evaluator:
            return EdgeCaseResult(
                question_id=item.id,
                category=item.category,
                passed=False,
                detail=f"Unknown edge case category: {item.category}",
            )

        return evaluator(item)

    def evaluate_all(self, items: List[EvalItem]) -> CategoryReport:
        """Run edge case evaluation on relevant items."""
        edge_categories = {"no_answer", "cross_protocol", "specificity", "ambiguous"}
        scorable = [item for item in items if item.category in edge_categories]
        self._logger.info("Evaluating edge cases on %d/%d items", len(scorable), len(items))

        results: list[EdgeCaseResult] = []
        for item in scorable:
            result = self.evaluate_item(item)
            results.append(result)
            self._logger.info(
                "  Q%d (%s): %s â€” %s",
                item.id,
                item.category,
                "PASS" if result.passed else "FAIL",
                result.detail[:80],
            )

        if not results:
            return CategoryReport(
                category="edge_cases",
                score=0.0,
                status="fail",
                metrics={"pass_rate": 0.0, "evaluated_count": 0},
                details=[],
            )

        pass_rate = sum(1 for r in results if r.passed) / len(results)

        sub_categories = {}
        for cat in edge_categories:
            cat_results = [r for r in results if r.category == cat]
            if cat_results:
                cat_pass = sum(1 for r in cat_results if r.passed) / len(cat_results)
                sub_categories[cat] = {
                    "pass_rate": round(cat_pass, 3),
                    "total": len(cat_results),
                    "passed": sum(1 for r in cat_results if r.passed),
                }

        overall = pass_rate * 100

        if pass_rate >= 0.80:
            status = "pass"
        elif pass_rate >= 0.60:
            status = "warn"
        else:
            status = "fail"

        self._logger.info(
            "Edge case results â€” Pass rate: %.1f%% | Status: %s | Breakdown: %s",
            pass_rate * 100,
            status,
            sub_categories,
        )

        return CategoryReport(
            category="edge_cases",
            score=round(overall, 1),
            status=status,
            metrics={
                "pass_rate": round(pass_rate, 3),
                "evaluated_count": len(results),
                "subcategories": sub_categories,
            },
            details=[r.model_dump() for r in results],
        )
