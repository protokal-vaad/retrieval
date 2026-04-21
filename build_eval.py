"""Builds the RAG evaluation set — 40 questions across 6 categories."""
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


# ---------------------------------------------------------------------------
# Question bank — organised by category
# ---------------------------------------------------------------------------

_QUESTIONS: list[dict] = [
    # ── Round 1: Broad exploratory (category=broad) ──────────────────────
    {
        "round": 1,
        "category": "broad",
        "question": "אילו נושאים עלו לדיון בישיבות ועד ריחן?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 1,
        "category": "broad",
        "question": "מתי התקיימו ישיבות הוועד ומה היה סדר היום בכל אחת?",
        "expected_section_types": ["Header and Agenda"],
    },
    {
        "round": 1,
        "category": "broad",
        "question": "אילו החלטות התקבלו בישיבות הוועד?",
        "expected_section_types": ["Topic Discussion", "Closing and Decisions"],
    },
    {
        "round": 1,
        "category": "broad",
        "question": "מי השתתף בישיבות ועד ריחן?",
        "expected_section_types": ["Header and Agenda"],
    },
    {
        "round": 1,
        "category": "broad",
        "question": "מה הנושאים הכלכליים או התקציביים שנדונו בוועד?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 1,
        "category": "broad",
        "question": "מה הנושאים הקהילתיים שעלו בישיבות הוועד?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 1,
        "category": "broad",
        "question": "אילו ועדות הוקמו או פעלו במסגרת הוועד?",
        "expected_section_types": ["Topic Discussion"],
    },

    # ── Round 2: Specific follow-up (category=specific) ──────────────────
    {
        "round": 2,
        "category": "specific",
        "question": "מה הייתה ההחלטה שהתקבלה בנושא התחזוקה של השכונה?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "באיזו ישיבה נדון הנושא הדחוף ביותר ומה הוחלט?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "האם ישנן החלטות שנדחו לישיבה הבאה? אם כן, אילו?",
        "expected_section_types": ["Topic Discussion", "Closing and Decisions"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מי מבין חברי הוועד הגיש הצעה או יוזמה רשמית?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הסכום שאושר או נדון בהקשר לתקציב הוועד?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא מינוי מנכ\"ל חדש ליישוב?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא ועדת הגינון ותכניותיה?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה עלה בנושא פרסום הפרוטוקולים ושיטת ההפצה?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא דרך הגן והסדרי התנועה ביישוב?",
        "expected_section_types": ["Topic Discussion"],
    },

    # ── No-answer questions (category=no_answer) ─────────────────────────
    {
        "round": 3,
        "category": "no_answer",
        "question": "מה הוחלט בנושא בניית בית ספר חדש ביישוב?",
        "golden_answer": "אין מידע בפרוטוקולים על בניית בית ספר חדש.",
        "expected_section_types": [],
        "expected_source_files": [],
    },
    {
        "round": 3,
        "category": "no_answer",
        "question": "האם הוועד דן במדיניות החוץ של ישראל?",
        "golden_answer": "נושא זה לא נדון בישיבות הוועד.",
        "expected_section_types": [],
        "expected_source_files": [],
    },
    {
        "round": 3,
        "category": "no_answer",
        "question": "מה קרה בישיבת הוועד בשנת 2019?",
        "golden_answer": "אין פרוטוקולים מ-2019 במערכת.",
        "expected_section_types": [],
        "expected_source_files": [],
    },
    {
        "round": 3,
        "category": "no_answer",
        "question": "מה ההחלטה שהתקבלה בנוגע להקמת בריכת שחייה ציבורית?",
        "golden_answer": "אין מידע בפרוטוקולים על הקמת בריכת שחייה ציבורית.",
        "expected_section_types": [],
        "expected_source_files": [],
    },
    {
        "round": 3,
        "category": "no_answer",
        "question": "האם נדון נושא סיפוח ריחן לעיר אחרת?",
        "golden_answer": "נושא זה לא עלה בישיבות הוועד.",
        "expected_section_types": [],
        "expected_source_files": [],
    },
    {
        "round": 3,
        "category": "no_answer",
        "question": "מה הוחלט בנושא תחבורה ציבורית ליישוב?",
        "golden_answer": "אין מידע על דיון בתחבורה ציבורית בפרוטוקולים.",
        "expected_section_types": [],
        "expected_source_files": [],
    },

    # ── Cross-protocol questions (category=cross_protocol) ───────────────
    {
        "round": 4,
        "category": "cross_protocol",
        "question": "מה כל ההחלטות שהתקבלו בנושא גינון לאורך כל הישיבות?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 4,
        "category": "cross_protocol",
        "question": "איך השתנה המצב התקציבי של היישוב מישיבה לישיבה?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 4,
        "category": "cross_protocol",
        "question": "באילו ישיבות נדון נושא המנכ\"ל ומה הייתה ההתקדמות?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 4,
        "category": "cross_protocol",
        "question": "מה כל הפרויקטים שאושרו או נדחו לאורך שנת 2025?",
        "expected_section_types": ["Topic Discussion", "Closing and Decisions"],
    },
    {
        "round": 4,
        "category": "cross_protocol",
        "question": "האם יש נושאים שחוזרים על עצמם במספר ישיבות? אילו?",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 4,
        "category": "cross_protocol",
        "question": "מה ההיסטוריה של החלטות הוועד בנושא קיצוץ תקציבי?",
        "expected_section_types": ["Topic Discussion"],
    },

    # ── Specificity questions (category=specificity) ─────────────────────
    {
        "round": 5,
        "category": "specificity",
        "question": "מה הסכום שהיה בחשבון הפיתוח לפי ישיבה 08/25?",
        "golden_answer": "642,331 שקלים בחשבון הפיתוח.",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מי היה יו\"ר הוועד בישיבה שהתקיימה ב-30.03.25?",
        "golden_answer": "יצחק בוכניק היה יו\"ר הוועד.",
        "expected_section_types": ["Header and Agenda"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "כמה כסף הוחלט לקצץ מתקציב הגינון?",
        "golden_answer": "150,000 שקלים.",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מה הגירעון השנתי הצפוי שדווח בישיבה 08/25?",
        "golden_answer": "כ-400 אלף שקלים בשל אי תשלום מיסי אזור תעשיה רזפול.",
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "כמה חברי ועד מנויים ברשימת המשתתפים בישיבה 17/25?",
        "expected_section_types": ["Header and Agenda"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מה מספר הטלפון של משרד ועד ריחן?",
        "golden_answer": "04-6350257.",
        "expected_section_types": ["Header and Agenda"],
    },

    # ── Ambiguous questions (category=ambiguous) ─────────────────────────
    {
        "round": 6,
        "category": "ambiguous",
        "question": "מה המצב?",
        "expected_section_types": [],
    },
    {
        "round": 6,
        "category": "ambiguous",
        "question": "ספר לי על הוועד",
        "expected_section_types": [],
    },
    {
        "round": 6,
        "category": "ambiguous",
        "question": "מה חדש?",
        "expected_section_types": [],
    },
    {
        "round": 6,
        "category": "ambiguous",
        "question": "תגיד משהו על ריחן",
        "expected_section_types": [],
    },
]


def _run_questions(
    agent: RAGAgent,
    questions: list[dict],
    logger: logging.Logger,
) -> list[EvalItem]:
    """Run all questions through the RAG agent and build EvalItems."""
    items: list[EvalItem] = []

    for i, q in enumerate(questions, start=1):
        logger.info("[%d/%d] %s  (category=%s)", i, len(questions), q["question"], q["category"])
        result = agent.run(q["question"])
        previews = [doc.content[:120] for doc in result.source_documents]

        item = EvalItem(
            id=i,
            round=q["round"],
            category=q["category"],
            question=q["question"],
            answer=result.answer,
            golden_answer=q.get("golden_answer"),
            expected_source_files=q.get("expected_source_files", []),
            expected_section_types=q.get("expected_section_types", []),
            num_sources=len(result.source_documents),
            source_previews=previews,
        )
        items.append(item)

        answer_preview = result.answer[:200] + ("..." if len(result.answer) > 200 else "")
        print(f"  [{i}] {q['question']}")
        print(f"      Category: {q['category']} | Sources: {item.num_sources}")
        print(f"      Answer: {answer_preview}\n")

    return items


def _save_eval_set(items: list[EvalItem], output_path: str, logger: logging.Logger) -> None:
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
    logger.info("Building RAG evaluation set — %d questions across 6 categories.", len(_QUESTIONS))

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

    # Print category breakdown
    from collections import Counter
    cats = Counter(q["category"] for q in _QUESTIONS)
    print(f"\n{'=' * 70}")
    print(f"  BUILDING EVAL SET — {len(_QUESTIONS)} questions")
    print(f"  Categories: {dict(cats)}")
    print(f"{'=' * 70}\n")

    items = _run_questions(agent, _QUESTIONS, logger)
    _save_eval_set(items, "eval_set.json", logger)

    print(f"\nDone — {len(items)} questions processed.")
    print("Next step: review eval_set.json and validate golden answers.")


if __name__ == "__main__":
    main()
