import json
import logging
import os
import sys
from datetime import datetime, timezone

from src.agent import RAGAgent
from src.logger import AppLogger
from src.models import EvalItem, EvalSet
from src.retriever import FirestoreRetriever
from src.settings import Settings


_ROUND_1_QUESTIONS = [
    "אילו נושאים עלו לדיון בישיבות ועד ריחן?",
    "מתי התקיימו ישיבות הוועד ומה היה סדר היום בכל אחת?",
    "אילו החלטות התקבלו בישיבות הוועד?",
    "מי השתתף בישיבות ועד ריחן?",
    "מה הנושאים הכלכליים או התקציביים שנדונו בוועד?",
]

_ROUND_2_QUESTIONS = [
    "מה הייתה ההחלטה שהתקבלה בנושא התחזוקה של השכונה?",
    "באיזו ישיבה נדון הנושא הדחוף ביותר ומה הוחלט?",
    "האם ישנן החלטות שנדחו לישיבה הבאה? אם כן, אילו?",
    "מי מבין חברי הוועד הגיש הצעה או יוזמה רשמית?",
    "מה הסכום שאושר או נדון בהקשר לתקציב הוועד?",
]


def _run_round(
    agent: RAGAgent,
    questions: list,
    round_num: int,
    start_id: int,
    logger: logging.Logger,
) -> list:
    items = []
    label = "Broad Exploratory" if round_num == 1 else "Specific Follow-up"
    print(f"\n{'=' * 70}")
    print(f"  ROUND {round_num}  —  {label}")
    print(f"{'=' * 70}")

    for i, question in enumerate(questions, start=start_id):
        logger.info("[Round %d] Q%d: %s", round_num, i, question)
        result = agent.run(question)
        previews = [doc.content[:120] for doc in result.source_documents]
        item = EvalItem(
            id=i,
            round=round_num,
            question=result.question,
            answer=result.answer,
            num_sources=len(result.source_documents),
            source_previews=previews,
        )
        items.append(item)

        print(f"\n[{i}] {question}")
        answer_preview = result.answer[:300] + ("..." if len(result.answer) > 300 else "")
        print(f"    Answer: {answer_preview}")
        print(f"    Sources: {item.num_sources} doc(s)")

    return items


def _save_eval_set(items: list, output_path: str, logger: logging.Logger) -> None:
    eval_set = EvalSet(
        created_at=datetime.now(timezone.utc).isoformat(),
        total_items=len(items),
        items=items,
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(eval_set.model_dump(), f, ensure_ascii=False, indent=2)
    logger.info("Eval set saved to %s (%d items)", output_path, len(items))
    print(f"\nEval set saved to: {output_path}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    config = Settings()

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

    logger = AppLogger(level=config.LOG_LEVEL).get()
    logger.info("Building RAG evaluation set — 10 questions across 2 rounds.")

    retriever = FirestoreRetriever(
        project_id=config.GCP_PROJECT_ID,
        location=config.VERTEXAI_LOCATION,
        collection=config.FIRESTORE_COLLECTION,
        database=config.FIRESTORE_DATABASE,
        embedding_model=config.EMBEDDING_MODEL,
        logger=logger,
    )
    retriever.setup()

    agent = RAGAgent(
        model_name=config.MODEL_NAME,
        retriever=retriever,
        logger=logger,
    )
    agent.setup()

    round1_items = _run_round(agent, _ROUND_1_QUESTIONS, 1, 1, logger)
    round2_items = _run_round(agent, _ROUND_2_QUESTIONS, 2, 6, logger)

    _save_eval_set(round1_items + round2_items, "eval_set.json", logger)


if __name__ == "__main__":
    main()
