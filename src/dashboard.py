"""HTML Dashboard Generator — produces a visual evaluation report with Hebrew explanations."""
from src.models import EvalReport, EvalSet


_CATEGORY_LABELS = {
    "retrieval": {
        "title": "איכות שליפה (Retrieval)",
        "description": "האם המערכת שולפת את הקטעים הנכונים מהפרוטוקולים? בודק שהתוצאות רלוונטיות לשאלה.",
        "metrics_help": {
            "hit_rate": "Hit Rate — באיזה אחוז מהשאלות לפחות תוצאה אחת הייתה רלוונטית",
            "mrr": "MRR — באיזה מיקום ממוצע מופיעה התוצאה הרלוונטית הראשונה (1.0 = תמיד ראשונה)",
            "precision": "Precision — איזה אחוז מהתוצאות שנשלפו באמת רלוונטי",
        },
    },
    "answer": {
        "title": "איכות תשובות (Answer Quality)",
        "description": "האם התשובות מדויקות ומבוססות על המידע שנשלף? בודק נאמנות, רלוונטיות ושלמות.",
        "metrics_help": {
            "faithfulness_avg": "נאמנות — האם התשובה מבוססת רק על ה-context ולא ממציאה עובדות (1-5)",
            "relevance_avg": "רלוונטיות — האם התשובה עונה על השאלה שנשאלה (1-5)",
            "completeness_avg": "שלמות — האם התשובה מכסה את כל המידע הרלוונטי (1-5, רק לשאלות עם golden answer)",
        },
    },
    "chunking": {
        "title": "איכות חיתוך (Chunking Quality)",
        "description": "האם הפרוטוקולים חותכו נכון? בודק metadata, מבנה סקציות, קידוד עברית ומספר chunks.",
        "metrics_help": {
            "total_chunks": "סך הכל chunks במערכת",
            "total_files": "מספר קבצים מקור שונים",
            "total_issues": "מספר בעיות שנמצאו",
            "clean_file_rate": "אחוז הקבצים ללא בעיות",
        },
    },
    "edge_cases": {
        "title": "מקרי קצה (Edge Cases)",
        "description": "איך המערכת מתמודדת עם שאלות מיוחדות: שאלות שאין עליהן תשובה, שאלות חוצות-פרוטוקולים, שאלות ספציפיות ושאלות עמומות.",
        "metrics_help": {
            "pass_rate": "אחוז ההצלחה הכללי במקרי קצה",
        },
    },
}

_SUBCATEGORY_LABELS = {
    "no_answer": "שאלות ללא תשובה — האם המערכת מסרבת לענות כשאין מידע?",
    "cross_protocol": "שאלות חוצות-פרוטוקולים — האם המערכת שולפת ממספר ישיבות?",
    "specificity": "שאלות ספציפיות — האם המערכת מחזירה ערכים מדויקים (סכומים, תאריכים)?",
    "ambiguous": "שאלות עמומות — האם המערכת מתמודדת בצורה סבירה עם שאלות לא ברורות?",
}


def _status_color(status: str) -> str:
    return {"pass": "#22c55e", "warn": "#f59e0b", "fail": "#ef4444"}.get(status, "#6b7280")


def _status_icon(status: str) -> str:
    return {"pass": "&#10004;", "warn": "&#9888;", "fail": "&#10008;"}.get(status, "?")


def _status_label(status: str) -> str:
    return {"pass": "עובר", "warn": "אזהרה", "fail": "נכשל"}.get(status, status)


def _format_metric(key: str, value) -> str:
    if isinstance(value, float):
        if value <= 1.0 and key not in ("faithfulness_avg", "relevance_avg", "completeness_avg"):
            return f"{value:.1%}"
        return f"{value:.2f}"
    return str(value)


def generate_dashboard(report: EvalReport, eval_set: EvalSet, output_path: str) -> None:
    """Generate an HTML dashboard from the evaluation report."""

    # Build category cards
    category_cards = ""
    for cat in report.categories:
        info = _CATEGORY_LABELS.get(cat.category, {})
        title = info.get("title", cat.category)
        desc = info.get("description", "")
        metrics_help = info.get("metrics_help", {})
        color = _status_color(cat.status)
        icon = _status_icon(cat.status)
        label = _status_label(cat.status)

        # Metrics table rows
        metrics_rows = ""
        for key, value in cat.metrics.items():
            if key in ("evaluated_count", "completeness_count", "issues_by_type", "subcategories"):
                continue
            help_text = metrics_help.get(key, key)
            formatted = _format_metric(key, value)
            metrics_rows += f"""
                <tr>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; color: #374151; font-weight: 500;">{help_text}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; font-weight: 700; font-size: 1.1em;">{formatted}</td>
                </tr>"""

        # Subcategories for edge cases
        subcats_html = ""
        if cat.category == "edge_cases" and "subcategories" in cat.metrics:
            subcats_html = '<div style="margin-top: 16px;">'
            for sub_key, sub_data in cat.metrics["subcategories"].items():
                sub_label = _SUBCATEGORY_LABELS.get(sub_key, sub_key)
                sub_passed = sub_data.get("passed", 0)
                sub_total = sub_data.get("total", 0)
                sub_rate = sub_data.get("pass_rate", 0)
                sub_color = "#22c55e" if sub_rate >= 0.8 else "#f59e0b" if sub_rate >= 0.6 else "#ef4444"
                subcats_html += f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f3f4f6;">
                        <span style="color: #4b5563; font-size: 0.9em;">{sub_label}</span>
                        <span style="color: {sub_color}; font-weight: 700;">{sub_passed}/{sub_total}</span>
                    </div>"""
            subcats_html += "</div>"

        # Issues breakdown for chunking
        issues_html = ""
        if cat.category == "chunking" and "issues_by_type" in cat.metrics:
            issues_by_type = cat.metrics["issues_by_type"]
            if issues_by_type:
                issue_labels = {
                    "missing_metadata": "metadata חסר",
                    "bad_section_dist": "מבנה סקציות שגוי",
                    "encoding_error": "שגיאות קידוד",
                    "bad_chunk_count": "מספר chunks חריג",
                    "empty_content": "תוכן ריק",
                }
                issues_html = '<div style="margin-top: 16px;"><h4 style="margin: 0 0 8px 0; color: #6b7280; font-size: 0.85em;">פירוט בעיות:</h4>'
                for issue_type, count in issues_by_type.items():
                    issue_label = issue_labels.get(issue_type, issue_type)
                    issues_html += f'<span style="display: inline-block; background: #fef2f2; color: #991b1b; padding: 4px 10px; border-radius: 12px; margin: 2px 4px; font-size: 0.85em;">{issue_label}: {count}</span>'
                issues_html += "</div>"

        category_cards += f"""
        <div style="background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-right: 5px solid {color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h2 style="margin: 0; font-size: 1.3em; color: #1f2937;">{title}</h2>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 2em; font-weight: 800; color: {color};">{cat.score:.0f}</span>
                    <span style="background: {color}; color: white; padding: 4px 10px; border-radius: 8px; font-size: 0.85em; font-weight: 600;">{icon} {label}</span>
                </div>
            </div>
            <p style="color: #6b7280; margin: 0 0 16px 0; font-size: 0.95em; line-height: 1.6;">{desc}</p>
            <table style="width: 100%; border-collapse: collapse;">
                {metrics_rows}
            </table>
            {subcats_html}
            {issues_html}
        </div>"""

    # Build per-question table from eval set items + report details
    questions_rows = ""
    # Map question scores from answer report
    answer_details = {}
    for cat in report.categories:
        if cat.category == "answer":
            for d in cat.details:
                answer_details[d.get("question_id")] = d

    edge_details = {}
    for cat in report.categories:
        if cat.category == "edge_cases":
            for d in cat.details:
                edge_details[d.get("question_id")] = d

    for item in eval_set.items:
        cat_badge_color = {
            "broad": "#3b82f6", "specific": "#8b5cf6", "no_answer": "#ef4444",
            "cross_protocol": "#f59e0b", "specificity": "#06b6d4", "ambiguous": "#6b7280",
        }.get(item.category, "#9ca3af")

        cat_label = {
            "broad": "כללי", "specific": "ספציפי", "no_answer": "אין תשובה",
            "cross_protocol": "חוצה-פרוטוקולים", "specificity": "ערך מדויק", "ambiguous": "עמום",
        }.get(item.category, item.category)

        # Get scores
        answer_info = answer_details.get(item.id, {})
        faith = answer_info.get("faithfulness", {}).get("score", "—")
        relev = answer_info.get("relevance", {}).get("score", "—")
        compl_data = answer_info.get("completeness")
        compl = compl_data.get("score", "—") if compl_data else "—"

        edge_info = edge_details.get(item.id, {})
        edge_pass = edge_info.get("passed")
        edge_icon = ""
        if edge_pass is True:
            edge_icon = '<span style="color: #22c55e;">&#10004;</span>'
        elif edge_pass is False:
            edge_icon = '<span style="color: #ef4444;">&#10008;</span>'

        answer_preview = (item.answer[:150] + "...") if len(item.answer) > 150 else item.answer

        questions_rows += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px; font-weight: 600; color: #374151;">{item.id}</td>
                <td style="padding: 10px;"><span style="background: {cat_badge_color}; color: white; padding: 2px 8px; border-radius: 6px; font-size: 0.8em;">{cat_label}</span></td>
                <td style="padding: 10px; color: #1f2937; direction: rtl; text-align: right;">{item.question}</td>
                <td style="padding: 10px; color: #4b5563; direction: rtl; text-align: right; font-size: 0.9em; max-width: 350px; overflow: hidden; text-overflow: ellipsis;">{answer_preview}</td>
                <td style="padding: 10px; text-align: center; font-weight: 600;">{faith}</td>
                <td style="padding: 10px; text-align: center; font-weight: 600;">{relev}</td>
                <td style="padding: 10px; text-align: center; font-weight: 600;">{compl}</td>
                <td style="padding: 10px; text-align: center;">{item.num_sources}</td>
                <td style="padding: 10px; text-align: center;">{edge_icon}</td>
            </tr>"""

    overall_color = _status_color(report.overall_status)
    overall_icon = _status_icon(report.overall_status)
    overall_label = _status_label(report.overall_status)

    html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Protokal.AI — Evaluation Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f9fafb; color: #1f2937; direction: rtl; padding: 24px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ font-size: 1.8em; margin-bottom: 8px; }}
        .subtitle {{ color: #6b7280; margin-bottom: 24px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; margin-bottom: 32px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        th {{ background: #f3f4f6; padding: 12px 10px; text-align: right; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb; font-size: 0.85em; }}
        .legend {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        .legend h3 {{ margin-bottom: 12px; color: #374151; }}
        .legend-item {{ display: inline-block; margin: 4px 8px; padding: 4px 12px; border-radius: 8px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
            <div>
                <h1>Protokal.AI — דשבורד הערכה</h1>
                <p class="subtitle">נוצר: {report.created_at[:19].replace('T', ' ')} UTC | {eval_set.total_items} שאלות</p>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 3em; font-weight: 900; color: {overall_color};">{report.overall_score:.0f}</div>
                <div style="background: {overall_color}; color: white; padding: 6px 16px; border-radius: 8px; font-weight: 700; font-size: 1.1em;">{overall_icon} {overall_label}</div>
            </div>
        </div>

        <!-- Legend -->
        <div class="legend">
            <h3>מקרא סטטוסים</h3>
            <span class="legend-item" style="background: #dcfce7; color: #166534;">&#10004; עובר — העמידה ביעדים</span>
            <span class="legend-item" style="background: #fef9c3; color: #854d0e;">&#9888; אזהרה — קרוב לסף, דורש תשומת לב</span>
            <span class="legend-item" style="background: #fef2f2; color: #991b1b;">&#10008; נכשל — מתחת ליעד, דורש תיקון</span>
        </div>

        <!-- Category Cards -->
        <div class="grid">
            {category_cards}
        </div>

        <!-- Per-Question Table -->
        <h2 style="margin-bottom: 16px; font-size: 1.4em;">פירוט לפי שאלה</h2>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th style="width: 40px;">#</th>
                        <th style="width: 100px;">קטגוריה</th>
                        <th style="min-width: 200px;">שאלה</th>
                        <th style="min-width: 250px;">תשובה (תקציר)</th>
                        <th style="width: 70px; text-align: center;" title="נאמנות — האם התשובה נאמנה ל-context">נאמנות</th>
                        <th style="width: 70px; text-align: center;" title="רלוונטיות — האם התשובה עונה על השאלה">רלוונט</th>
                        <th style="width: 70px; text-align: center;" title="שלמות — האם התשובה מכסה את כל המידע">שלמות</th>
                        <th style="width: 60px; text-align: center;">מקורות</th>
                        <th style="width: 60px; text-align: center;" title="תוצאת מקרה קצה">קצה</th>
                    </tr>
                </thead>
                <tbody>
                    {questions_rows}
                </tbody>
            </table>
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 32px; padding: 16px; color: #9ca3af; font-size: 0.85em;">
            Protokal.AI Evaluation Framework | Generated automatically by run_eval.py
        </div>
    </div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
