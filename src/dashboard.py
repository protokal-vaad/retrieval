"""HTML dashboard generator for a client-facing RAG evaluation work document."""

from html import escape

from src.models import EvalReport, EvalSet


_CATEGORY_INFO = {
    "retrieval": {
        "title": "1. בדיקות שליפה",
        "subtitle": "האם המערכת מביאה את הקטעים הנכונים מהפרוטוקולים לפני שהיא עונה",
        "why": "אם השליפה לא טובה, גם תשובה שנשמעת טוב יכולה להיות מבוססת על מסמכים לא נכונים.",
        "score_meaning": "הציון משקף עד כמה השאלה מגיעה למסמך הנכון, כמה מהר הוא מופיע, וכמה מהתוצאות באמת רלוונטיות.",
        "metric_labels": {
            "hit_rate": "Hit Rate",
            "mrr": "MRR",
            "precision": "Precision",
            "evaluated_count": "שאלות שנמדדו",
        },
        "metric_help": {
            "hit_rate": "באיזה אחוז מהשאלות לפחות אחד מהקטעים שנשלפו היה נכון.",
            "mrr": "כמה גבוה הופיע הקטע הנכון בתוצאות. גבוה יותר אומר שהשליפה מגיעה מהר לדברים הנכונים.",
            "precision": "מתוך כל הקטעים שנשלפו, כמה מהם באמת היו רלוונטיים.",
            "evaluated_count": "לא כל שאלה מודדת שליפה. כאן רואים בכמה שאלות באמת היה יעד שליפה מוגדר.",
        },
        "client_fields": [
            ("expected_source_files", "מגדיר מאילו פרוטוקולים אנחנו מצפים שהמערכת תשלוף מידע."),
            ("expected_section_types", "מגדיר איזה סוג חלק במסמך אמור להכיל את התשובה."),
        ],
    },
    "answer": {
        "title": "2. בדיקות תשובה",
        "subtitle": "האם התשובה עצמה נכונה, ממוקדת, ומכסה את מה שחשוב",
        "why": "המטרה העסקית היא לא רק למצוא מסמך, אלא לתת תשובה שאפשר לסמוך עליה.",
        "score_meaning": "הציון משלב נאמנות למקור, רלוונטיות לשאלה, ושלמות מול תשובת ייחוס כאשר קיימת.",
        "metric_labels": {
            "faithfulness_avg": "נאמנות",
            "relevance_avg": "רלוונטיות",
            "completeness_avg": "שלמות",
            "completeness_count": "שאלות עם תשובת ייחוס",
            "evaluated_count": "שאלות שנמדדו",
        },
        "metric_help": {
            "faithfulness_avg": "האם התשובה נאמנה לטקסט שנשלף, בלי להמציא פרטים.",
            "relevance_avg": "האם התשובה באמת עונה על השאלה שנשאלה.",
            "completeness_avg": "כאשר יש תשובת ייחוס, האם התשובה מכסה את כל העובדות החשובות.",
            "completeness_count": "מספר השאלות שיש להן כרגע תשובת ייחוס ולכן אפשר למדוד בהן שלמות.",
            "evaluated_count": "כמה שאלות השתתפו במדידת איכות התשובה.",
        },
        "client_fields": [
            ("golden_answer", "זו תשובת הייחוס של הלקוח. היא מה שמאפשר למדוד שלמות ולא רק תחושה כללית."),
            ("answer", "זו תשובת הבסיס שהמערכת מחזירה כרגע, כדי להשוות שינויים לאורך זמן."),
        ],
    },
    "chunking": {
        "title": "3. בדיקות מבנה הנתונים",
        "subtitle": "האם הפרוטוקולים מפורקים לקטעים בצורה נקייה ושימושית לשליפה",
        "why": "גם מודל טוב יתקשה אם המסמכים נשמרו עם metadata חסר, קידוד שבור, או חלוקה לא טובה.",
        "score_meaning": "הציון משקף את שיעור הקבצים הנקיים מבעיות מבנה, metadata ותוכן.",
        "metric_labels": {
            "total_chunks": "סה\"כ קטעים",
            "total_files": "סה\"כ קבצי מקור",
            "total_issues": "סה\"כ בעיות",
            "clean_file_rate": "שיעור קבצים נקיים",
        },
        "metric_help": {
            "total_chunks": "כמה קטעים קיימים היום בוקטור סטור.",
            "total_files": "כמה קבצים שונים נסרקו והפכו לקטעים.",
            "total_issues": "כמה בעיות מבנה נמצאו בכלל הקבצים.",
            "clean_file_rate": "באיזה אחוז מהקבצים לא נמצאה אף בעיית מבנה.",
        },
        "client_fields": [
            ("source_previews", "נותן תחושת בקרה על הקטעים שהמערכת באמת רואה."),
        ],
    },
    "edge_cases": {
        "title": "4. בדיקות התנהגות מיוחדת",
        "subtitle": "איך המערכת מתנהגת כששואלים שאלות קשות, עמומות, או בלי תשובה אמיתית",
        "why": "אלה בדיוק המצבים שפוגעים באמון המשתמש אם המערכת נשמעת בטוחה מדי או מפספסת הקשר.",
        "score_meaning": "הציון מראה בכמה מהמקרים המיוחדים המערכת התנהגה כמו שהיינו רוצים בעולם אמיתי.",
        "metric_labels": {
            "pass_rate": "שיעור הצלחה",
            "evaluated_count": "שאלות שנמדדו",
        },
        "metric_help": {
            "pass_rate": "באיזה אחוז ממקרי הקצה המערכת התנהגה נכון.",
            "evaluated_count": "כמה שאלות שייכות כרגע למקרי קצה.",
        },
        "client_fields": [
            ("category", "סוג השאלה קובע איזה מבחן התנהגות המערכת צריכה לעבור."),
        ],
    },
}

_QUESTION_CATEGORY_LABELS = {
    "broad": "שאלה כללית",
    "specific": "שאלה ספציפית",
    "no_answer": "שאלה ללא תשובה",
    "cross_protocol": "שאלה חוצת פרוטוקולים",
    "specificity": "שאלת ערך מדויק",
    "ambiguous": "שאלה עמומה",
}

_QUESTION_CATEGORY_HELP = {
    "broad": "בודקת האם המערכת יודעת לסכם נושא רחב ממסמכים רלוונטיים.",
    "specific": "בודקת האם המערכת עונה נכון על החלטה או פרט מוגדר.",
    "no_answer": "בודקת האם המערכת יודעת להודות שאין מידע במקום להמציא.",
    "cross_protocol": "בודקת האם המערכת מחברת מידע מכמה ישיבות שונות.",
    "specificity": "בודקת האם ערכים כמו סכומים, תאריכים ושמות יוצאים בדיוק הנדרש.",
    "ambiguous": "בודקת האם המערכת מגיבה בזהירות לשאלה כללית מדי.",
}

_EDGE_SUBCATEGORY_LABELS = {
    "no_answer": "אין תשובה",
    "cross_protocol": "חוצה פרוטוקולים",
    "specificity": "ערך מדויק",
    "ambiguous": "עמום",
}


def _status_color(status: str) -> str:
    return {"pass": "#1f9d55", "warn": "#b7791f", "fail": "#c53030"}.get(status, "#4a5568")


def _status_label(status: str) -> str:
    return {"pass": "תקין", "warn": "דורש תשומת לב", "fail": "דורש תיקון"}.get(status, status)


def _format_metric(key: str, value: object) -> str:
    if isinstance(value, float):
        if key in {"hit_rate", "mrr", "precision", "clean_file_rate", "pass_rate"}:
            return f"{value:.1%}"
        return f"{value:.2f}"
    return str(value)


def _nl_to_br(text: str) -> str:
    return escape(text).replace("\n", "<br>")


def _build_detail_maps(report: EvalReport) -> tuple[dict[int, dict], dict[int, dict], dict[int, dict]]:
    retrieval_details: dict[int, dict] = {}
    answer_details: dict[int, dict] = {}
    edge_details: dict[int, dict] = {}

    for category in report.categories:
        if category.category == "retrieval":
            for detail in category.details:
                retrieval_details[detail.get("question_id")] = detail
        elif category.category == "answer":
            for detail in category.details:
                answer_details[detail.get("question_id")] = detail
        elif category.category == "edge_cases":
            for detail in category.details:
                edge_details[detail.get("question_id")] = detail

    return retrieval_details, answer_details, edge_details


def _question_metric_impact(item) -> str:
    impacts = []
    if item.expected_source_files or item.expected_section_types:
        impacts.append("שליפה")
    if item.answer:
        impacts.append("תשובה")
    if item.golden_answer:
        impacts.append("שלמות")
    if item.category in {"no_answer", "cross_protocol", "specificity", "ambiguous"}:
        impacts.append("מקרי קצה")
    return ", ".join(impacts) if impacts else "תיעוד בלבד"


def _question_action(item, retrieval_info: dict, answer_info: dict, edge_info: dict) -> str:
    if not item.golden_answer and item.category in {"specific", "specificity"}:
        return "להוסיף תשובת ייחוס כדי למדוד שלמות במדויק."
    if (item.expected_source_files or item.expected_section_types) and not retrieval_info:
        return "להשלים ציפיית שליפה או לוודא שהשאלה נמדדת נכון."
    if answer_info:
        completeness = answer_info.get("completeness")
        if completeness and completeness.get("missing_facts"):
            return "לחדד את תשובת הייחוס או לוודא שהמערכת מחזירה גם את העובדות החסרות."
    if edge_info and edge_info.get("passed") is False:
        return "לבדוק אם ההתנהגות המצופה הוגדרה נכון ואם התשובה באמת תומכת במטרה העסקית."
    return "נראה תקין כרגע; אפשר להשתמש בפריט הזה כעוגן להשוואה עתידית."


def _render_scoreboard(report: EvalReport) -> str:
    cards = []
    for category in report.categories:
        info = _CATEGORY_INFO.get(category.category, {})
        color = _status_color(category.status)
        rows = []
        for key, value in category.metrics.items():
            if key in {"issues_by_type", "subcategories"}:
                continue
            rows.append(
                f"""
                <div class="metric-row">
                    <div>
                        <div class="metric-name">{escape(info.get("metric_labels", {}).get(key, key))}</div>
                        <div class="metric-help">{escape(info.get("metric_help", {}).get(key, ""))}</div>
                    </div>
                    <div class="metric-value">{escape(_format_metric(key, value))}</div>
                </div>"""
            )

        extra = ""
        if category.category == "chunking":
            issues = category.metrics.get("issues_by_type", {})
            if issues:
                chips = "".join(
                    f'<span class="chip chip-danger">{escape(issue_type)}: {escape(str(count))}</span>'
                    for issue_type, count in issues.items()
                )
                extra = f'<div class="sub-block"><div class="sub-title">פירוט בעיות מבנה</div><div>{chips}</div></div>'

        if category.category == "edge_cases":
            subcategories = category.metrics.get("subcategories", {})
            if subcategories:
                sub_rows = "".join(
                    f"""
                    <div class="mini-row">
                        <span>{escape(_EDGE_SUBCATEGORY_LABELS.get(name, name))}</span>
                        <strong>{escape(str(data.get("passed", 0)))}/{escape(str(data.get("total", 0)))}</strong>
                    </div>"""
                    for name, data in subcategories.items()
                )
                extra = f'<div class="sub-block"><div class="sub-title">פירוט מקרי קצה</div>{sub_rows}</div>'

        field_rows = "".join(
            f"<li><strong>{escape(field)}</strong>: {escape(help_text)}</li>"
            for field, help_text in info.get("client_fields", [])
        )

        cards.append(
            f"""
            <section class="panel category-panel">
                <div class="panel-head">
                    <div>
                        <h3>{escape(info.get("title", category.category))}</h3>
                        <p class="muted">{escape(info.get("subtitle", ""))}</p>
                    </div>
                    <div class="score-badge" style="border-color: {color}; color: {color};">
                        <div class="score-number">{category.score:.0f}</div>
                        <div class="score-status">{escape(_status_label(category.status))}</div>
                    </div>
                </div>
                <div class="explain-grid">
                    <div>
                        <div class="sub-title">מה נבדק כאן</div>
                        <p>{escape(info.get("why", ""))}</p>
                    </div>
                    <div>
                        <div class="sub-title">איך לקרוא את הציון</div>
                        <p>{escape(info.get("score_meaning", ""))}</p>
                    </div>
                </div>
                <div class="metrics-list">{''.join(rows)}</div>
                {extra}
                <div class="sub-block">
                    <div class="sub-title">איזה שדות בטבלת השאלות משפיעים על המדד הזה</div>
                    <ul class="field-list">{field_rows}</ul>
                </div>
            </section>"""
        )

    return "".join(cards)


def _render_questions_table(eval_set: EvalSet, report: EvalReport) -> str:
    retrieval_details, answer_details, edge_details = _build_detail_maps(report)
    rows = []

    for item in eval_set.items:
        retrieval_info = retrieval_details.get(item.id, {})
        answer_info = answer_details.get(item.id, {})
        edge_info = edge_details.get(item.id, {})

        retrieval_summary = "לא נמדד"
        if retrieval_info:
            retrieval_summary = (
                f"Hit: {'כן' if retrieval_info.get('hit') else 'לא'} | "
                f"MRR: {_format_metric('mrr', retrieval_info.get('reciprocal_rank', 0.0))} | "
                f"Precision: {_format_metric('precision', retrieval_info.get('precision', 0.0))}"
            )

        answer_summary = "לא נמדד"
        if answer_info:
            faith = answer_info.get("faithfulness", {}).get("score", "—")
            relevance = answer_info.get("relevance", {}).get("score", "—")
            completeness_data = answer_info.get("completeness")
            completeness = completeness_data.get("score", "—") if completeness_data else "—"
            answer_summary = f"נאמנות {faith}/5 | רלוונטיות {relevance}/5 | שלמות {completeness}/5"

        edge_summary = "לא נמדד"
        if edge_info:
            edge_summary = f"{'עבר' if edge_info.get('passed') else 'נכשל'} | {edge_info.get('detail', '')}"

        expected_sources = ", ".join(item.expected_source_files) if item.expected_source_files else "—"
        expected_sections = ", ".join(item.expected_section_types) if item.expected_section_types else "—"
        golden_answer = item.golden_answer or "חסר כרגע"
        previews = "<br>".join(escape(preview[:120]) for preview in item.source_previews[:2]) or "—"

        rows.append(
            f"""
            <tr>
                <td>{item.id}</td>
                <td>
                    <div><strong>{escape(_QUESTION_CATEGORY_LABELS.get(item.category, item.category))}</strong></div>
                    <div class="cell-help">{escape(_QUESTION_CATEGORY_HELP.get(item.category, ""))}</div>
                </td>
                <td class="rtl">{_nl_to_br(item.question)}</td>
                <td>{escape(_question_metric_impact(item))}</td>
                <td class="rtl">{_nl_to_br(item.answer[:220] + ('...' if len(item.answer) > 220 else ''))}</td>
                <td class="rtl">{_nl_to_br(golden_answer[:220] + ('...' if len(golden_answer) > 220 else ''))}</td>
                <td class="rtl">
                    <div><strong>קבצים:</strong> {escape(expected_sources)}</div>
                    <div class="cell-help"><strong>חלקים:</strong> {escape(expected_sections)}</div>
                </td>
                <td class="rtl">{_nl_to_br(retrieval_summary)}</td>
                <td class="rtl">{_nl_to_br(answer_summary)}</td>
                <td class="rtl">{_nl_to_br(edge_summary)}</td>
                <td class="rtl">{previews}</td>
                <td class="rtl">{escape(_question_action(item, retrieval_info, answer_info, edge_info))}</td>
            </tr>"""
        )

    return "".join(rows)


def generate_dashboard(report: EvalReport, eval_set: EvalSet, output_path: str) -> None:
    """Generate a client-facing HTML work document from the evaluation report."""

    overall_color = _status_color(report.overall_status)
    intro_panels = """
        <section class="panel intro-panel">
            <h2>מה המסמך הזה נותן</h2>
            <div class="intro-grid">
                <div>
                    <h3>1. מה נבדק ולמה זה חשוב</h3>
                    <p>כל אזור במסמך מסביר בשפה פשוטה איזה חלק של מערכת ה-RAG נבדק ואיך זה קשור להצלחת הפרויקט בפועל.</p>
                </div>
                <div>
                    <h3>2. מצב נוכחי במספרים</h3>
                    <p>הציונים מראים איפה המערכת חזקה כרגע ואיפה צריך שיפור, כדי שאפשר יהיה למדוד התקדמות בין ריצות.</p>
                </div>
                <div>
                    <h3>3. מסמך עבודה ללקוח</h3>
                    <p>טבלת השאלות נועדה לא רק להצגה, אלא גם לשיפור השאלות, תשובות הייחוס, וציפיות השליפה שמגדירות את הבנצ'מרק.</p>
                </div>
            </div>
        </section>
        <section class="panel intro-panel">
            <h2>איך לקרוא את טבלת השאלות</h2>
            <div class="intro-grid">
                <div>
                    <h3>שאלה ותשובת בסיס</h3>
                    <p>זו התנהגות המערכת היום. זו נקודת ההשוואה לכל שינוי עתידי.</p>
                </div>
                <div>
                    <h3>תשובת ייחוס</h3>
                    <p>כאשר יש תשובת ייחוס, אפשר למדוד שלמות ולא רק התרשמות כללית. זה המקום הכי חשוב לשיתוף פעולה עם הלקוח.</p>
                </div>
                <div>
                    <h3>ציפיית שליפה</h3>
                    <p>קובעת מאילו מסמכים או מאיזה סוג קטע אנחנו מצפים שהתשובה תבוא. בלי זה קשה לדעת אם השליפה באמת הצליחה.</p>
                </div>
                <div>
                    <h3>תוצאות לפי שאלה</h3>
                    <p>כל שורה מראה איך אותה שאלה השפיעה על שליפה, על איכות התשובה, ועל מקרי קצה אם רלוונטי.</p>
                </div>
            </div>
        </section>
    """

    html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Protokal.AI Evaluation Work Document</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: #f4f6f8; color: #1f2933; font-family: Arial, Helvetica, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 1480px; margin: 0 auto; padding: 24px; }}
        .hero {{ background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 28px; margin-bottom: 24px; }}
        .hero-grid {{ display: grid; grid-template-columns: 1.6fr 0.8fr; gap: 20px; align-items: start; }}
        .hero h1 {{ margin: 0 0 8px; font-size: 32px; }}
        .muted {{ color: #52606d; }}
        .overall-box {{ border: 2px solid {overall_color}; border-radius: 8px; padding: 18px; text-align: center; color: {overall_color}; }}
        .overall-score {{ font-size: 56px; font-weight: 700; line-height: 1; }}
        .panel {{ background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 24px; margin-bottom: 24px; }}
        .intro-grid {{ display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap: 18px; }}
        .cards-grid {{ display: grid; grid-template-columns: repeat(2, minmax(320px, 1fr)); gap: 20px; }}
        .panel-head {{ display: flex; justify-content: space-between; align-items: start; gap: 16px; margin-bottom: 18px; }}
        .score-badge {{ min-width: 110px; border: 2px solid; border-radius: 8px; padding: 10px 12px; text-align: center; }}
        .score-number {{ font-size: 34px; font-weight: 700; line-height: 1; }}
        .score-status {{ margin-top: 6px; font-size: 14px; }}
        .explain-grid {{ display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 18px; margin-bottom: 18px; }}
        .sub-title {{ font-weight: 700; margin-bottom: 6px; }}
        .metrics-list {{ border-top: 1px solid #e4e7eb; }}
        .metric-row {{ display: grid; grid-template-columns: 1fr auto; gap: 12px; padding: 12px 0; border-bottom: 1px solid #e4e7eb; }}
        .metric-name {{ font-weight: 700; }}
        .metric-help {{ color: #52606d; font-size: 14px; }}
        .metric-value {{ font-weight: 700; white-space: nowrap; }}
        .sub-block {{ margin-top: 18px; padding-top: 16px; border-top: 1px solid #e4e7eb; }}
        .field-list {{ margin: 0; padding-right: 18px; }}
        .field-list li {{ margin-bottom: 8px; }}
        .chip {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 13px; margin: 4px 6px 0 0; }}
        .chip-danger {{ background: #fde8e8; color: #9b1c1c; }}
        .mini-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f4f8; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9e2ec; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px; border-bottom: 1px solid #e4e7eb; vertical-align: top; text-align: right; font-size: 14px; }}
        th {{ background: #f0f4f8; font-size: 13px; }}
        .rtl {{ direction: rtl; }}
        .cell-help {{ color: #52606d; font-size: 12px; margin-top: 4px; }}
        .footer {{ color: #7b8794; font-size: 12px; text-align: center; padding: 8px 0 24px; }}
        @media (max-width: 980px) {{
            .hero-grid, .cards-grid, .intro-grid, .explain-grid {{ grid-template-columns: 1fr; }}
            .container {{ padding: 16px; }}
            .hero h1 {{ font-size: 28px; }}
            .overall-score {{ font-size: 46px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <section class="hero">
            <div class="hero-grid">
                <div>
                    <h1>מסמך עבודה להערכת RAG</h1>
                    <p class="muted">המסמך הזה מחבר בין בדיקות המערכת, ציוני המדדים, וטבלת העבודה של השאלות והתשובות במקום אחד.</p>
                    <p class="muted">נוצר: {escape(report.created_at[:19].replace('T', ' '))} UTC | מספר שאלות במסמך: {eval_set.total_items}</p>
                </div>
                <div class="overall-box">
                    <div class="overall-score">{report.overall_score:.0f}</div>
                    <div>{escape(_status_label(report.overall_status))}</div>
                </div>
            </div>
        </section>

        {intro_panels}

        <section class="cards-grid">
            {_render_scoreboard(report)}
        </section>

        <section class="panel">
            <h2>טבלת העבודה המלאה של השאלות</h2>
            <p class="muted">זו הטבלה שהלקוח והצוות יכולים לעבוד עליה יחד. כל שורה מראה מה נמדד, למה זה משפיע, ומה כדאי להשלים או לחדד.</p>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>סוג שאלה</th>
                            <th>שאלה</th>
                            <th>על אילו מדדים היא משפיעה</th>
                            <th>תשובת בסיס</th>
                            <th>תשובת ייחוס</th>
                            <th>ציפיית שליפה</th>
                            <th>תוצאת שליפה</th>
                            <th>תוצאת תשובה</th>
                            <th>תוצאת מקרה קצה</th>
                            <th>תצוגת מקורות</th>
                            <th>פעולה מומלצת</th>
                        </tr>
                    </thead>
                    <tbody>
                        {_render_questions_table(eval_set, report)}
                    </tbody>
                </table>
            </div>
        </section>

        <div class="footer">Generated by Protokal.AI evaluation pipeline</div>
    </div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html)
