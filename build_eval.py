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
    # =====================================================================
    # Round 1: Broad exploratory (category=broad)
    # No source_files — answer may come from many meetings.
    # =====================================================================
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

    # =====================================================================
    # Round 2: Specific topic — each grounded in one or two specific protocols.
    # `expected_source_files` uses substrings that match the stored filename
    # (e.g. "11.25" matches both `פרוטוקול ועד 11.25.pdf` and `.pdf.docx`).
    # =====================================================================
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא צמצום פעילות קבלן הגינון בישיבה 11/25?",
        "golden_answer": "הוועד החליט להפסיק את חוזה הגינון במתכונתו הנוכחית ולפתוח מכרז גינון חדש שישקף תקציב מופחת, כדי לקצץ 150,000 ₪ ולהעביר לתקציב חינוך בלתי פורמלי.",
        "expected_source_files": ["11.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא מינוי מנכ\"ל קבע ליישוב?",
        "golden_answer": "הוועד החליט למנות את אוריאל שקד כמנכ\"ל הקבע של היישוב (ישיבה 04/25).",
        "expected_source_files": ["4.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט לגבי החלפת יו\"ר הוועד?",
        "golden_answer": "יצחק בוכניק הודיע על סיום כהונתו לפני השלמת 18 חודשים, והוועד בחר פה אחד באייל קלמן כיו\"ר החדש (ישיבה 14/25).",
        "expected_source_files": ["14.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מי נבחר כקבלן הגינון החדש לתקופת יולי-דצמבר 2025?",
        "golden_answer": "אייל לוי, חבר האגודה, נבחר מבין 6 הצעות מחיר (ישיבה 16/25).",
        "expected_source_files": ["16.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה עלה בנושא פרסום הפרוטוקולים ושיטת ההפצה?",
        "golden_answer": "הוחלט שאחרי עריכת הפרוטוקול ואישור היו\"ר, הוא יישלח לאורן בודנר שיתמצת אותו דרך מערכת ה-AI \"פרוטוקל\", התמצית תחולק לנושאים משותפים ולהחלטות, תאושר ע\"י המנכ\"ל, ותופץ יחד עם הפרוטוקולים החתומים.",
        "expected_source_files": ["17.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא העלאת תעריפי הארנונה לשנת 2026?",
        "golden_answer": "הוועד אישר פה אחד העלאת ארנונה של 1.626% בהתאם לשיעור שנקבע ע\"י משרד הפנים (ישיבה 13/25).",
        "expected_source_files": ["13.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא סמלי המעון ליישוב?",
        "golden_answer": "סמל המעון יישאר לבינתיים בבעלות המועצה; היישוב ישלם השתתפות חודשית של 500 ₪ והמועצה תישא באחריות הדיווח למשרד החינוך (ישיבה 16/25).",
        "expected_source_files": ["16.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא הצעת מכולת בריחן?",
        "golden_answer": "הוועד החליט לקדם את מיזם המכולת של דור בוכניק בקונספט שירות עצמי, בכפוף לבדיקת חלופות מיקום ואישור המועצה והיישוב (ישיבה 05/25).",
        "expected_source_files": ["5.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנוגע לקבלת החבר שחר אלידע לוועד?",
        "golden_answer": "שחר אלידע הוזמן כבא בתור ברשימת הבחירות והחל לכהן כחבר ועד מן המניין, במקום דן בר-אל שעזב (ישיבה 05/25).",
        "expected_source_files": ["5.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא העלאת שכר המזכירה?",
        "golden_answer": "השכר יועלה באופן מידתי בכפוף לתוספת שעות נוספות חודשיות (ישיבה 03/25).",
        "expected_source_files": ["3.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הייתה התוכנית להתמודדות עם סכנות שריפות ביישוב?",
        "golden_answer": "הוצגה תכנית להכשרה והצטיידות של כיתת כוננות אש ממתנדבים תושבי היישוב בעלות של כ-200,000 ₪, שתועלה להצבעה באסיפה (ישיבה 14/25).",
        "expected_source_files": ["14.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 2,
        "category": "specific",
        "question": "מה הוחלט בנושא הקצאת שטח לקרול שדה?",
        "golden_answer": "הוועד אישר את מתווה המיזם ויחתום על הסכם, לאחר שקרול חתמה על מסמך מאומת ע\"י נוטריון המעיד על מודעותה לסיכונים של התב\"ע העתידית (ישיבה 04/25).",
        "expected_source_files": ["4.25"],
        "expected_section_types": ["Topic Discussion"],
    },

    # =====================================================================
    # Round 3: No-answer — information is not in the protocols at all.
    # =====================================================================
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
        "question": "מה הוחלט בנושא הקמת קו אוטובוס חדש מריחן לחיפה?",
        "golden_answer": "אין מידע בפרוטוקולים על הקמת קו אוטובוס לחיפה.",
        "expected_section_types": [],
        "expected_source_files": [],
    },
    {
        "round": 3,
        "category": "no_answer",
        "question": "כמה חברי ועד פרשו לפנסיה בשנת 2025?",
        "golden_answer": "אין מידע על פרישה לפנסיה של חברי ועד בפרוטוקולים.",
        "expected_section_types": [],
        "expected_source_files": [],
    },

    # =====================================================================
    # Round 4: Cross-protocol — answer must span multiple meetings.
    # =====================================================================
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
    {
        "round": 4,
        "category": "cross_protocol",
        "question": "איך התפתחה התקדמות בנושא חברת הרי זהב ותשלומי המיסים לאורך הישיבות?",
        "expected_section_types": ["Topic Discussion"],
    },

    # =====================================================================
    # Round 5: Specificity — precise numbers, dates, names from specific files.
    # =====================================================================
    {
        "round": 5,
        "category": "specificity",
        "question": "מה הסכום שהיה בחשבון הפיתוח לפי ישיבה 08/25?",
        "golden_answer": "642,331 ₪ בחשבון הפיתוח.",
        "expected_source_files": ["08.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מי היה יו\"ר הוועד בישיבה שהתקיימה ב-30.03.25?",
        "golden_answer": "יצחק בוכניק היה יו\"ר הוועד (ישיבה 08/25).",
        "expected_source_files": ["08.25", "30.03.25"],
        "expected_section_types": ["Header and Agenda"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "כמה כסף הוחלט לקצץ מתקציב הגינון?",
        "golden_answer": "150,000 ₪ (הקיצוץ הועבר לתקציב חינוך בלתי פורמלי).",
        "expected_source_files": ["11.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מה הגירעון השנתי הצפוי שדווח בישיבה 08/25?",
        "golden_answer": "כ-400 אלף ₪ בשל אי תשלום מיסי אזור תעשיה רזפול.",
        "expected_source_files": ["08.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מה מספר הטלפון של משרד ועד ריחן?",
        "golden_answer": "04-6350257.",
        "expected_section_types": ["Header and Agenda"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מה תעריף ההעלאה שאושר בצו הארנונה לשנת 2026?",
        "golden_answer": "1.626% כשיעור שנקבע ע\"י משרד הפנים.",
        "expected_source_files": ["13.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מי מונה כמנכ\"ל הקבע של היישוב ובאיזו ישיבה?",
        "golden_answer": "אוריאל שקד מונה כמנכ\"ל הקבע של היישוב, בישיבה 04/25 (09.02.25).",
        "expected_source_files": ["4.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מה הייתה עלות התוכנית להכשרת כיתת כוננות האש?",
        "golden_answer": "כ-200,000 ₪ (ישיבה 14/25).",
        "expected_source_files": ["14.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "מה היה הסכום בחשבון הפיתוח לפי דו\"ח התזרים מיום 22/06/2025?",
        "golden_answer": "802,344 ₪ בחשבון הפיתוח (ישיבה 15/25).",
        "expected_source_files": ["15.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 5,
        "category": "specificity",
        "question": "כמה סגרו פרויקטים 2024-2025 חריגה מהתקציב, לפי ישיבה 11/25?",
        "golden_answer": "כלל הפרויקטים 2024-2025 לא חרגו מתקציב שאושר (ישיבה 11/25).",
        "expected_source_files": ["11.25"],
        "expected_section_types": ["Topic Discussion"],
    },

    # =====================================================================
    # Round 6: Ambiguous — testing graceful handling of vague questions.
    # =====================================================================
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

    # =====================================================================
    # Round 7: Person-based — retrieval should find the right speaker/role.
    # =====================================================================
    {
        "round": 7,
        "category": "specific",
        "question": "מי מילא את תפקיד מזכיר הישיבות בישיבות הוועד ב-2025?",
        "golden_answer": "אוריאל שקד שימש כמזכיר רוב הישיבות ב-2025.",
        "expected_section_types": ["Header and Agenda"],
    },
    {
        "round": 7,
        "category": "specific",
        "question": "מי הציג את תוכנית התב\"ע העתידית בפני הוועד?",
        "golden_answer": "אורן ספרים הופיע בפני הוועד והעיר על תוכנית התב\"ע; המליץ על הקמת \"ועדת תב\"ע\" לבחינת השפעות על הסביבה (ישיבה 07/25).",
        "expected_source_files": ["07.25", "7.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 7,
        "category": "specific",
        "question": "מי הציג את סקירת סכנות השריפות ביישוב?",
        "golden_answer": "יניב שלום, סגן ומ\"מ רבש\"ץ ריחן, הציג את הסקירה (ישיבה 14/25).",
        "expected_source_files": ["14.25"],
        "expected_section_types": ["Topic Discussion"],
    },

    # =====================================================================
    # Round 8: Yes/No decisions — tests binary answer correctness.
    # =====================================================================
    {
        "round": 8,
        "category": "specific",
        "question": "האם תקציב 2025 של היישוב אושר באסיפה הכללית שב-09/02?",
        "golden_answer": "לא. תקציב 2025 לא עבר את אישור האסיפה הכללית ב-09/02, ולכן מונתה ועדת תקציב מיוחדת (ישיבה 05/25).",
        "expected_source_files": ["5.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 8,
        "category": "specific",
        "question": "האם הוועד אישר פה אחד את צו הארנונה לשנת 2026?",
        "golden_answer": "כן. צו הארנונה אושר פה אחד בישיבה 13/25 (03.06.25), כולל התייקרות של 1.626%.",
        "expected_source_files": ["13.25"],
        "expected_section_types": ["Topic Discussion"],
    },
    {
        "round": 8,
        "category": "specific",
        "question": "האם הוכרה ההיעדרות של מנהלת הפעוטון כתאונת עבודה?",
        "golden_answer": "לא. הוועד החליט שלא מדובר בתאונת עבודה, מכיוון שהיציאה מהיישוב הייתה ללא אישור וללא ידיעה (ישיבה 01/25).",
        "expected_source_files": ["1.25"],
        "expected_section_types": ["Topic Discussion"],
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
