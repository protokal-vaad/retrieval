"""Main evaluation runner — executes all 4 eval modules and produces report + dashboard."""
import json
import os
import sys
import webbrowser
from datetime import datetime, timezone

from build_eval import build_eval_set
from src.settings import Settings
from src.logger import AppLogger
from src.models import EvalSet, EvalReport, CategoryReport
from src.retriever import FirestoreRetriever
from src.agent import RAGAgent
from src.judge import JudgeAgent
from src.eval_retrieval import RetrievalEvaluator
from src.eval_answer import AnswerEvaluator
from src.eval_chunking import ChunkingEvaluator
from src.eval_edge_cases import EdgeCaseEvaluator
from src.dashboard import generate_dashboard


def _load_eval_set(path: str) -> EvalSet:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return EvalSet(**data)


def _compute_overall(categories: list[CategoryReport]) -> tuple[float, str]:
    """Compute weighted overall score and status."""
    weights = {"retrieval": 0.30, "answer": 0.35, "chunking": 0.15, "edge_cases": 0.20}
    total_weight = 0.0
    weighted_sum = 0.0

    for cat in categories:
        w = weights.get(cat.category, 0.25)
        weighted_sum += cat.score * w
        total_weight += w

    overall = weighted_sum / total_weight if total_weight else 0.0

    if all(c.status == "pass" for c in categories):
        status = "pass"
    elif any(c.status == "fail" for c in categories):
        status = "fail"
    else:
        status = "warn"

    return round(overall, 1), status


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    config = Settings()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

    logger = AppLogger(level=config.LOG_LEVEL).get()

    # Rebuild the eval set from the current question bank before scoring.
    logger.info("Rebuilding eval set from current _QUESTIONS before evaluation.")
    build_eval_set(output_path="eval_set.json")

    # Load fresh eval set
    eval_set = _load_eval_set("eval_set.json")
    logger.info("Loaded eval set: %d items", eval_set.total_items)

    # Initialize shared components
    retriever = FirestoreRetriever(
        sa_path=config.GOOGLE_APPLICATION_CREDENTIALS,
        project_id=config.GCP_PROJECT_ID,
        location=config.VERTEXAI_LOCATION,
        collection=config.FIRESTORE_COLLECTION,
        database=config.FIRESTORE_DATABASE,
        embedding_model=config.EMBEDDING_MODEL,
        embedding_dimensions=config.EMBEDDING_DIMENSIONS,
        logger=logger,
    )
    retriever.setup()

    agent = RAGAgent(
        model_name=config.MODEL_NAME,
        retriever=retriever,
        logger=logger,
    )
    agent.setup()

    judge = JudgeAgent(
        model_name=config.MODEL_NAME,
        logger=logger,
    )
    judge.setup()

    categories: list[CategoryReport] = []

    # ── 1. Retrieval Quality ─────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("  [1/4] Retrieval Quality")
    print(f"{'=' * 60}")
    retrieval_eval = RetrievalEvaluator(retriever=retriever, logger=logger)
    retrieval_report = retrieval_eval.evaluate_all(eval_set.items)
    categories.append(retrieval_report)
    print(f"  Score: {retrieval_report.score} | Status: {retrieval_report.status}")
    print(f"  Hit Rate: {retrieval_report.metrics.get('hit_rate')} | MRR: {retrieval_report.metrics.get('mrr')} | Precision: {retrieval_report.metrics.get('precision')}")

    # ── 2. Answer Quality ────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("  [2/4] Answer Quality")
    print(f"{'=' * 60}")
    answer_eval = AnswerEvaluator(judge=judge, retriever=retriever, logger=logger)
    answer_report = answer_eval.evaluate_all(eval_set.items)
    categories.append(answer_report)
    print(f"  Score: {answer_report.score} | Status: {answer_report.status}")
    print(f"  Faithfulness: {answer_report.metrics.get('faithfulness_avg')} | Relevance: {answer_report.metrics.get('relevance_avg')} | Completeness: {answer_report.metrics.get('completeness_avg')}")

    # ── 3. Chunking Quality ──────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("  [3/4] Chunking Quality")
    print(f"{'=' * 60}")
    chunking_eval = ChunkingEvaluator(
        project_id=config.GCP_PROJECT_ID,
        database_id=config.FIRESTORE_DATABASE,
        collection_name=config.FIRESTORE_COLLECTION,
        logger=logger,
    )
    chunking_report = chunking_eval.evaluate_all()
    categories.append(chunking_report)
    print(f"  Score: {chunking_report.score} | Status: {chunking_report.status}")
    print(f"  Chunks: {chunking_report.metrics.get('total_chunks')} | Files: {chunking_report.metrics.get('total_files')} | Issues: {chunking_report.metrics.get('total_issues')}")

    # ── 4. Edge Cases ────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("  [4/4] Edge Cases")
    print(f"{'=' * 60}")
    edge_eval = EdgeCaseEvaluator(retriever=retriever, agent=agent, logger=logger)
    edge_report = edge_eval.evaluate_all(eval_set.items)
    categories.append(edge_report)
    print(f"  Score: {edge_report.score} | Status: {edge_report.status}")
    subcats = edge_report.metrics.get("subcategories", {})
    for sub_name, sub_data in subcats.items():
        print(f"    {sub_name}: {sub_data.get('passed')}/{sub_data.get('total')} passed")

    # ── Build final report ───────────────────────────────────────────────
    overall_score, overall_status = _compute_overall(categories)

    report = EvalReport(
        created_at=datetime.now(timezone.utc).isoformat(),
        categories=categories,
        overall_score=overall_score,
        overall_status=overall_status,
    )

    # Save JSON report
    report_path = "eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)

    # Generate HTML dashboard
    dashboard_path = "eval_dashboard.html"
    generate_dashboard(report, eval_set, dashboard_path)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  OVERALL SCORE: {overall_score}/100  [{overall_status.upper()}]")
    print(f"{'=' * 60}")
    for cat in categories:
        icon = {"pass": "[OK]", "warn": "[!!]", "fail": "[XX]"}.get(cat.status, "[??]")
        print(f"  {icon} {cat.category:15s} {cat.score:6.1f}/100  ({cat.status})")
    print(f"{'=' * 60}")
    print(f"\n  Report:    {report_path}")
    print(f"  Dashboard: {dashboard_path}")

    # Open dashboard unless explicitly disabled for automated or headless runs.
    if os.getenv("PROTOKAL_OPEN_DASHBOARD", "1") == "1":
        webbrowser.open(os.path.abspath(dashboard_path))


if __name__ == "__main__":
    main()
