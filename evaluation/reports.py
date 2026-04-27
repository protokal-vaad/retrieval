"""Three separate HTML reports built from an existing EvalReport + EvalSet.

No evaluation is executed here. All data is read from the JSON outputs of
`run_eval.py` (eval_report.json, eval_set.json) and rendered into:

  - Client Work Report     (client-facing benchmark worksheet)
  - Technical Report       (data-scientist deep-dive over every metric)
  - Client Summary Report  (executive 0-100% snapshot with 4 business KPIs)
"""

from html import escape

from evaluation.models import CategoryReport, EvalReport, EvalSet


# ---------------------------------------------------------------------------
# Shared definitions
# ---------------------------------------------------------------------------

# Weights used by run_eval._compute_overall — kept in sync so the technical
# report can show the formula and the summary report can show contribution %.
CATEGORY_WEIGHTS = {
    "retrieval": 0.30,
    "answer": 0.35,
    "chunking": 0.15,
    "edge_cases": 0.20,
}

# Maps the four eval categories to the four business-friendly KPIs the
# Client Summary Report must show.
BUSINESS_KPI = {
    "answer": {
        "title": "איכות התשובות הסופיות",
        "subtitle": "Final Answer Quality",
        "explain": (
            "האם התשובות מלאות, מדויקות, ונאמנות למסמכים — בלי הזיות. "
            "נמדד מול תשובות ייחוס שאושרו ידנית."
        ),
    },
    "retrieval": {
        "title": "יכולת איתור המידע",
        "subtitle": "Information Retrieval Ability",
        "explain": (
            "האם המערכת שולפת מבסיס הנתונים את המסמכים והקטעים הנכונים "
            "לפני שהיא מנסחת תשובה."
        ),
    },
    "edge_cases": {
        "title": "אמינות במצבי קיצון",
        "subtitle": "Reliability in Edge Cases",
        "explain": (
            "האם המערכת אומרת \"אני לא יודע\" כשחסר מידע, וכיצד היא מתמודדת "
            "עם שאלות עמומות ושאלות שחוצות כמה פרוטוקולים."
        ),
    },
    "chunking": {
        "title": "תקינות בסיס הנתונים",
        "subtitle": "Database Integrity",
        "explain": (
            "מדד טכני שמשקף את איכות הסידור והחיתוך של הקבצים בבסיס הנתונים "
            "האחורי שמזין את המערכת."
        ),
    },
}

QUESTION_CATEGORY_LABELS = {
    "broad": "שאלה כללית",
    "specific": "שאלה ספציפית",
    "no_answer": "שאלה ללא תשובה",
    "cross_protocol": "שאלה חוצת פרוטוקולים",
    "specificity": "שאלת ערך מדויק",
    "ambiguous": "שאלה עמומה",
}

QUESTION_CATEGORY_HELP = {
    "broad": "בודקת האם המערכת יודעת לסכם נושא רחב ממסמכים רלוונטיים.",
    "specific": "בודקת האם המערכת עונה נכון על החלטה או פרט מוגדר.",
    "no_answer": "בודקת האם המערכת יודעת להודות שאין מידע במקום להמציא.",
    "cross_protocol": "בודקת האם המערכת מחברת מידע מכמה ישיבות שונות.",
    "specificity": "בודקת האם ערכים כמו סכומים, תאריכים ושמות יוצאים בדיוק הנדרש.",
    "ambiguous": "בודקת האם המערכת מגיבה בזהירות לשאלה כללית מדי.",
}


# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------

def _status_color(status: str) -> str:
    return {"pass": "#1f9d55", "warn": "#b7791f", "fail": "#c53030"}.get(status, "#4a5568")


def _status_label(status: str) -> str:
    return {"pass": "תקין", "warn": "דורש תשומת לב", "fail": "דורש תיקון"}.get(status, status)


def _nl_to_br(text: str) -> str:
    return escape(text).replace("\n", "<br>")


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _category_by_name(report: EvalReport) -> dict[str, CategoryReport]:
    return {c.category: c for c in report.categories}


def _question_by_id(eval_set: EvalSet) -> dict[int, object]:
    return {item.id: item for item in eval_set.items}


def _score_status(score: float) -> str:
    if score >= 80:
        return "pass"
    if score >= 60:
        return "warn"
    return "fail"


def _detail_maps(report: EvalReport) -> tuple[dict[int, dict], dict[int, dict], dict[int, dict]]:
    """Index per-question details by question id for fast lookup."""
    retrieval, answer, edge = {}, {}, {}
    for cat in report.categories:
        if cat.category == "retrieval":
            for d in cat.details:
                retrieval[d["question_id"]] = d
        elif cat.category == "answer":
            for d in cat.details:
                answer[d["question_id"]] = d
        elif cat.category == "edge_cases":
            for d in cat.details:
                edge[d["question_id"]] = d
    return retrieval, answer, edge


def _shared_css() -> str:
    return """
        * { box-sizing: border-box; }
        body { margin: 0; background: #f4f6f8; color: #1f2933; font-family: Arial, Helvetica, sans-serif; line-height: 1.6; }
        .container { max-width: 1480px; margin: 0 auto; padding: 24px; }
        .hero { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 28px; margin-bottom: 24px; }
        .hero h1 { margin: 0 0 8px; font-size: 32px; }
        .muted { color: #52606d; }
        .panel { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 24px; margin-bottom: 24px; }
        .sub-title { font-weight: 700; margin-bottom: 6px; }
        table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9e2ec; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px; border-bottom: 1px solid #e4e7eb; vertical-align: top; text-align: right; font-size: 14px; }
        th { background: #f0f4f8; font-size: 13px; }
        .rtl { direction: rtl; }
        .cell-help { color: #52606d; font-size: 12px; margin-top: 4px; }
        .footer { color: #7b8794; font-size: 12px; text-align: center; padding: 8px 0 24px; }
        .chip { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 13px; margin: 4px 6px 0 0; background: #e4e7eb; color: #1f2933; }
        .chip-danger { background: #fde8e8; color: #9b1c1c; }
        .chip-warn { background: #fef3c7; color: #92400e; }
        .chip-ok { background: #dcfce7; color: #166534; }
    """


def _html_doc(title: str, body: str, extra_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <style>
        {_shared_css()}
        {extra_css}
    </style>
</head>
<body>
    <div class="container">
        {body}
        <div class="footer">Generated by Protokal.AI evaluation pipeline</div>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# 1. Client Work Report  (דוח עבודה ללקוח)
# ---------------------------------------------------------------------------

def _render_client_work_table(eval_set: EvalSet, report: EvalReport) -> str:
    retrieval_details, answer_details, edge_details = _detail_maps(report)
    rows = []
    for item in eval_set.items:
        retrieval_info = retrieval_details.get(item.id, {})
        answer_info = answer_details.get(item.id, {})
        edge_info = edge_details.get(item.id, {})

        expected_sources = ", ".join(item.expected_source_files) if item.expected_source_files else "—"
        expected_sections = ", ".join(item.expected_section_types) if item.expected_section_types else "—"
        golden = item.golden_answer or "חסר — להשלים"
        golden_class = "" if item.golden_answer else "class=\"missing\""

        rows.append(f"""
            <tr>
                <td>{item.id}</td>
                <td>
                    <div><strong>{escape(QUESTION_CATEGORY_LABELS.get(item.category, item.category))}</strong></div>
                    <div class="cell-help">{escape(QUESTION_CATEGORY_HELP.get(item.category, ""))}</div>
                </td>
                <td class="rtl">{_nl_to_br(item.question)}</td>
                <td class="rtl" {golden_class}>{_nl_to_br(golden)}</td>
                <td class="rtl">
                    <div><strong>קבצים:</strong> {escape(expected_sources)}</div>
                    <div class="cell-help"><strong>סוגי קטע:</strong> {escape(expected_sections)}</div>
                </td>
            </tr>""")
    return "".join(rows)


def render_client_work_report(report: EvalReport, eval_set: EvalSet) -> str:
    """Produce the HTML for the client-facing benchmark worksheet."""

    missing_golden = [it for it in eval_set.items if not it.golden_answer and it.category in {"specific", "specificity"}]
    missing_sources = [it for it in eval_set.items if not it.expected_source_files and it.category in {"specific", "specificity", "cross_protocol"}]

    intro = f"""
        <section class="hero">
            <h1>דוח עבודה ללקוח</h1>
            <p class="muted">המסמך הזה הוא בנצ'מרק חי של מערכת ה-RAG. כל שורה מייצגת שאלה שאמורה להיענות ממסמכי הוועד.</p>
            <p class="muted">סך כל השאלות: <strong>{eval_set.total_items}</strong> | נוצר: {escape(report.created_at[:19].replace('T', ' '))} UTC</p>
        </section>

        <section class="panel">
            <h2>למה הקובץ הזה חשוב</h2>
            <p>בסיס הנתונים של הבנצ'מרק קובע איך נמדדת איכות המערכת. ככל שהשדות בטבלה מדויקים יותר, ככה הציון משקף יותר טוב את התנהגות המערכת מול שאלות אמיתיות.</p>

            <div class="sub-title">מה צריך לעשות בקובץ הזה</div>
            <ul>
                <li><strong>תשובת ייחוס (Golden Answer)</strong> — לכתוב לכל שאלה ספציפית את התשובה הנכונה. בלי זה אי אפשר למדוד שלמות אמיתית.</li>
                <li><strong>ציפיית שליפה</strong> — להזין מאיזה קובץ או סוג קטע התשובה אמורה לבוא. זה הציר שמודד את כושר השליפה.</li>
                <li><strong>סוג שאלה</strong> — לוודא שהקטגוריה משקפת באמת את אופי השאלה (ספציפית? עמומה? בלי תשובה?).</li>
            </ul>
        </section>

        <section class="panel">
            <h2>סטטוס שלמות הבנצ'מרק</h2>
            <div>
                <span class="chip chip-warn">תשובות ייחוס חסרות לשאלות ספציפיות: {len(missing_golden)}</span>
                <span class="chip chip-warn">ציפיות שליפה חסרות לשאלות מבוססות עובדות: {len(missing_sources)}</span>
            </div>
        </section>
    """

    table = f"""
        <section class="panel">
            <h2>טבלת השאלות לעבודה</h2>
            <p class="muted">יש להשלים שדות חסרים, לחדד תשובות ייחוס, ולעדכן ציפיות שליפה. כל שינוי כאן ישפיע על הריצה הבאה של ההערכה.</p>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>סוג שאלה</th>
                            <th>שאלה</th>
                            <th>תשובת ייחוס</th>
                            <th>ציפיית שליפה</th>
                        </tr>
                    </thead>
                    <tbody>
                        {_render_client_work_table(eval_set, report)}
                    </tbody>
                </table>
            </div>
        </section>
    """

    extra_css = """
        td.missing, [class~="missing"] { background: #fff7ed; color: #9a3412; }
    """
    return _html_doc("Protokal.AI — Client Work Report", intro + table, extra_css)


# ---------------------------------------------------------------------------
# 2. Technical Report  (דוח טכני)
# ---------------------------------------------------------------------------

def _render_weights_formula(report: EvalReport) -> str:
    """Show how each category contributes to the overall score."""
    by_name = _category_by_name(report)
    rows = []
    for cat_name, weight in CATEGORY_WEIGHTS.items():
        cat = by_name.get(cat_name)
        if not cat:
            continue
        contrib = cat.score * weight
        rows.append(f"""
            <tr>
                <td>{escape(cat_name)}</td>
                <td>{cat.score:.1f}</td>
                <td>{weight:.0%}</td>
                <td>{contrib:.2f}</td>
                <td><span class="chip chip-{ {'pass':'ok','warn':'warn','fail':'danger'}.get(cat.status,'ok') }">{escape(_status_label(cat.status))}</span></td>
            </tr>""")
    return "".join(rows)


def _render_retrieval_details(cat: CategoryReport) -> str:
    rows = []
    for d in cat.details:
        hit_chip = '<span class="chip chip-ok">hit</span>' if d.get("hit") else '<span class="chip chip-danger">miss</span>'
        rows.append(f"""
            <tr>
                <td>{d.get("question_id")}</td>
                <td>{hit_chip}</td>
                <td>{d.get("reciprocal_rank", 0):.3f}</td>
                <td>{d.get("precision", 0):.3f}</td>
            </tr>""")
    return "".join(rows)


def _render_answer_details(cat: CategoryReport) -> str:
    rows = []
    for d in cat.details:
        f = d.get("faithfulness") or {}
        r = d.get("relevance") or {}
        c = d.get("completeness")
        completeness_cell = "—"
        missing_cell = "—"
        if c:
            completeness_cell = f"{c.get('score', '—')}/5"
            mf = c.get("missing_facts") or []
            missing_cell = "<br>".join(escape(x) for x in mf) if mf else "—"
        rows.append(f"""
            <tr>
                <td>{d.get("question_id")}</td>
                <td>{f.get("score", "—")}/5</td>
                <td class="rtl cell-help">{_nl_to_br(f.get("reasoning", ""))}</td>
                <td>{r.get("score", "—")}/5</td>
                <td class="rtl cell-help">{_nl_to_br(r.get("reasoning", ""))}</td>
                <td>{completeness_cell}</td>
                <td class="rtl cell-help">{missing_cell}</td>
            </tr>""")
    return "".join(rows)


def _render_chunking_details(cat: CategoryReport) -> str:
    rows = []
    for d in cat.details:
        rows.append(f"""
            <tr>
                <td class="rtl">{escape(d.get("source_file", ""))}</td>
                <td><span class="chip chip-warn">{escape(d.get("issue_type", ""))}</span></td>
                <td class="rtl">{escape(d.get("detail", ""))}</td>
            </tr>""")
    return "".join(rows)


def _render_edge_details(cat: CategoryReport) -> str:
    rows = []
    for d in cat.details:
        chip = '<span class="chip chip-ok">passed</span>' if d.get("passed") else '<span class="chip chip-danger">failed</span>'
        rows.append(f"""
            <tr>
                <td>{d.get("question_id")}</td>
                <td>{escape(d.get("category", ""))}</td>
                <td>{chip}</td>
                <td class="rtl">{escape(d.get("detail", ""))}</td>
            </tr>""")
    return "".join(rows)


def _render_metrics_block(metrics: dict) -> str:
    """Flat list of category-level metrics (skips nested structures)."""
    rows = []
    for key, value in metrics.items():
        if isinstance(value, (dict, list)):
            continue
        if isinstance(value, float):
            display = f"{value:.3f}"
        else:
            display = str(value)
        rows.append(f"""
            <div class="metric-row">
                <div class="metric-name">{escape(key)}</div>
                <div class="metric-value">{escape(display)}</div>
            </div>""")
    return "".join(rows)


def _render_explanation_list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _render_chunking_issue_glossary(cat: CategoryReport) -> str:
    issue_examples: dict[str, list[dict]] = {}
    for detail in cat.details:
        issue_examples.setdefault(detail.get("issue_type", "unknown"), []).append(detail)

    descriptions = {
        "empty_content": (
            "קטע ריק או קצר מדי. בקוד כל קטע קצר מ-50 תווים נספר כבעיה, ולכן "
            "השגיאה לא אומרת בהכרח שהקובץ שבור אלא שהחיתוך יצר קטע חלש מדי לשימוש."
        ),
        "missing_metadata": (
            "מטא-דאטה חסרה או לא תקינה. כאן נבדקים `source_file`, `section_type`, "
            "ו-`document_date`, וגם האם `section_type` שייך לאחת הקטגוריות המותרות."
        ),
        "bad_section_dist": (
            "פיזור מקטעים לא סביר בתוך מסמך בודד. הבדיקה מצפה בדרך כלל ל-Header אחד, "
            "לפחות Topic Discussion אחד, ולכל היותר Closing אחד."
        ),
        "bad_chunk_count": (
            "מספר מקטעים חריג למסמך. בקוד כל מסמך עם פחות מ-2 מקטעים או יותר מ-20 "
            "מסומן כדי לאתר חיתוך חסר או חיתוך יתר."
        ),
        "encoding_error": (
            "נמצאו תווי Unicode שבורים (`U+FFFD`), מה שמרמז על פגיעה בטקסט בזמן חילוץ או המרה."
        ),
    }

    blocks = []
    for issue_type, description in descriptions.items():
        examples = issue_examples.get(issue_type, [])
        if not examples:
            continue
        example_lines = "".join(
            f"<li><strong>{escape(example.get('source_file', ''))}</strong> — {escape(example.get('detail', ''))}</li>"
            for example in examples[:3]
        )
        blocks.append(f"""
            <div class="issue-card">
                <div class="sub-title">{escape(issue_type)} ({len(examples)})</div>
                <div class="muted">{escape(description)}</div>
                <ul>{example_lines}</ul>
            </div>
        """)
    return "".join(blocks)


def _render_question_review_queue(report: EvalReport, eval_set: EvalSet) -> str:
    retrieval_details, answer_details, edge_details = _detail_maps(report)
    questions = _question_by_id(eval_set)

    flagged_ids = set()
    for question_id, detail in retrieval_details.items():
        if (not detail.get("hit")) or detail.get("reciprocal_rank", 0) < 1.0 or detail.get("precision", 0) < 1.0:
            flagged_ids.add(question_id)
    for question_id, detail in answer_details.items():
        faith = (detail.get("faithfulness") or {}).get("score", 5)
        relevance = (detail.get("relevance") or {}).get("score", 5)
        completeness = (detail.get("completeness") or {}).get("score", 5)
        if faith < 5 or relevance < 5 or completeness < 5:
            flagged_ids.add(question_id)
    for question_id, detail in edge_details.items():
        if not detail.get("passed"):
            flagged_ids.add(question_id)

    rows = []
    for question_id in sorted(flagged_ids):
        item = questions.get(question_id)
        if not item:
            continue

        retrieval = retrieval_details.get(question_id)
        answer = answer_details.get(question_id)
        edge = edge_details.get(question_id)

        retrieval_summary = "—"
        if retrieval:
            retrieval_summary = (
                f"hit={'yes' if retrieval.get('hit') else 'no'} | "
                f"RR={retrieval.get('reciprocal_rank', 0):.3f} | "
                f"precision={retrieval.get('precision', 0):.3f}"
            )

        answer_summary = "—"
        if answer:
            faith = (answer.get("faithfulness") or {}).get("score", "—")
            relevance = (answer.get("relevance") or {}).get("score", "—")
            completeness = (answer.get("completeness") or {}).get("score")
            answer_summary = f"faith={faith}/5 | rel={relevance}/5"
            if completeness is not None:
                answer_summary += f" | compl={completeness}/5"

        edge_summary = "—"
        if edge:
            edge_summary = edge.get("detail", "—")

        rows.append(f"""
            <tr>
                <td>{question_id}</td>
                <td>{escape(QUESTION_CATEGORY_LABELS.get(item.category, item.category))}</td>
                <td class="rtl">{_nl_to_br(item.question)}</td>
                <td class="rtl">{escape(retrieval_summary)}</td>
                <td class="rtl">{escape(answer_summary)}</td>
                <td class="rtl">{_nl_to_br(edge_summary)}</td>
            </tr>
        """)

    if not rows:
        return "<p class=\"muted\">No flagged questions in this run.</p>"

    return f"""
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>id</th>
                        <th>סוג שאלה</th>
                        <th>שאלה</th>
                        <th>Retrieval signal</th>
                        <th>Answer signal</th>
                        <th>Edge-case signal</th>
                    </tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    """


def render_technical_report(report: EvalReport, eval_set: EvalSet) -> str:
    """Detailed report for data scientists: methodology, formulas, and smart drill-down."""

    by_name = _category_by_name(report)
    overall_color = _status_color(report.overall_status)

    hero = f"""
        <section class="hero">
            <h1>דוח טכני</h1>
            <p class="muted">פירוט טכני מלא של כל המדדים, כל התוצאות לכל שאלה, ואיך הם מתחברים לציון הסופי.</p>
            <p class="muted">eval_report.created_at: {escape(report.created_at)} | total_items: {eval_set.total_items}</p>
            <div class="overall-banner" style="border-color: {overall_color}; color: {overall_color};">
                <div class="overall-number">{report.overall_score:.1f} / 100</div>
                <div>Overall status: {escape(_status_label(report.overall_status))}</div>
            </div>
        </section>
    """

    weights_table = f"""
        <section class="panel">
            <h2>נוסחת הציון הכולל</h2>
            <p class="muted">overall = Σ(category_score × weight) / Σ(weights). הטבלה מראה את התרומה של כל קטגוריה לציון של {report.overall_score:.1f}.</p>
            <table>
                <thead>
                    <tr><th>קטגוריה</th><th>ציון</th><th>משקל</th><th>תרומה</th><th>סטטוס</th></tr>
                </thead>
                <tbody>{_render_weights_formula(report)}</tbody>
            </table>
        </section>
    """

    sections = [hero, weights_table]

    if "retrieval" in by_name:
        cat = by_name["retrieval"]
        sections.append(f"""
            <section class="panel">
                <h2>1. Retrieval — ציון {cat.score:.1f}</h2>
                <p class="muted">זהו מדד דטרמיניסטי לחלוטין. הקוד ב-<code>src/eval_retrieval.py</code> מריץ שליפה ל-4 קטעים לכל שאלה ומשווה את התוצאה לציפיות שהוגדרו ב-<code>eval_set.json</code>.</p>
                <div class="metrics-list">{_render_metrics_block(cat.metrics)}</div>
                {_render_explanation_list([
                    "<strong>hit_rate</strong> — אחוז השאלות שבהן לפחות קטע אחד מתוך 4 הקטעים שנשלפו תאם את קובץ המקור או את סוג הקטע המצופה.",
                    "<strong>mrr</strong> — ממוצע <code>1 / rank</code> של הקטע הרלוונטי הראשון. אם הקטע הראשון נכון מקבלים 1.0, אם רק השני נכון מקבלים 0.5, ואם אין התאמה מקבלים 0.",
                    "<strong>precision</strong> — כמה מהקטעים שנשלפו היו רלוונטיים בפועל. בדוח הזה הממוצע הוא 0.53, כלומר בדרך כלל רק קצת יותר מחצי מההקשרים שנשלפו אכן התאימו.",
                    "<strong>score formula</strong> — הציון מחושב ישירות בקוד כך: <code>hit_rate*50 + mrr*30 + precision*20</code>.",
                ])}
            </section>
        """)

    if "answer" in by_name:
        cat = by_name["answer"]
        sections.append(f"""
            <section class="panel">
                <h2>2. Answer — ציון {cat.score:.1f}</h2>
                <p class="muted">זהו המדד היחיד בדוח שנשען על <strong>LLM-as-Judge</strong>. הקוד ב-<code>src/eval_answer.py</code> שולף שוב את ההקשר, ואז <code>src/judge.py</code> מפעיל שלושה שופטים מבוססי Pydantic AI עבור Faithfulness, Relevance ו-Completeness.</p>
                <div class="metrics-list">{_render_metrics_block(cat.metrics)}</div>
                {_render_explanation_list([
                    "<strong>faithfulness_avg</strong> — האם התשובה נשארת נאמנה לטקסטים שנשלפו, בלי להוסיף פרטים שלא הופיעו בהקשר.",
                    "<strong>relevance_avg</strong> — האם התשובה באמת עונה לשאלה שנשאלה, ולא רק קשורה אליה באופן כללי.",
                    "<strong>completeness_avg</strong> — נמדד רק בשאלות שיש להן <code>golden_answer</code>. השופט משווה בין תשובת המערכת לתשובת הייחוס ומחזיר גם <code>missing_facts</code>.",
                    "<strong>score formula</strong> — כל ממוצע מומר מסולם 1-5 ל-0-100 בעזרת <code>(avg-1)/4*100</code>, ואז מחושב <code>faith*0.4 + relevance*0.4 + completeness*0.2</code>.",
                    f"<strong>בפועל בריצה הזו</strong> — Completeness חושב רק עבור {cat.metrics.get('completeness_count', 0)} שאלות מתוך {cat.metrics.get('evaluated_count', 0)}, ולכן הפערים שם משקפים בעיקר איכות תשובות הייחוס והכיסוי העובדתי.",
                ])}
            </section>
        """)

    if "chunking" in by_name:
        cat = by_name["chunking"]
        issues_by_type = cat.metrics.get("issues_by_type", {})
        chips = "".join(
            f'<span class="chip chip-danger">{escape(k)}: {v}</span>'
            for k, v in issues_by_type.items()
        ) or "—"
        sections.append(f"""
            <section class="panel">
                <h2>3. Chunking — ציון {cat.score:.1f}</h2>
                <p class="muted">זהו מדד תשתיתי ודטרמיניסטי. הקוד ב-<code>src/eval_chunking.py</code> עובר על כל 667 הקטעים ב-Firestore, מקבץ אותם לפי קובץ מקור, ובודק איכות תוכן, מטא-דאטה, פיזור section types, ומספר chunk-ים למסמך.</p>
                <div class="metrics-list">{_render_metrics_block(cat.metrics)}</div>
                <div style="margin: 12px 0;"><strong>Issues by type:</strong> {chips}</div>
                {_render_explanation_list([
                    "<strong>clean_file_rate</strong> — אחוז הקבצים שלא נמצאה בהם אף בעיה. זהו גם הציון עצמו: <code>(clean files / total files) * 100</code>.",
                    "<strong>issues_by_type</strong> — ספירת בעיות גולמית, לא ציון. אותו קובץ יכול להופיע כמה פעמים אם נמצאו בו כמה בעיות שונות.",
                    "<strong>למה זה חשוב</strong> — Chunking לא מודד תשובות ללקוח אלא את איכות חומר הגלם שהשליפה והמודל מקבלים לפני שהם עונים.",
                ])}
                <h3>מה כל issue type אומר בפועל</h3>
                <div class="issue-grid">{_render_chunking_issue_glossary(cat)}</div>
                <h3>Per-issue</h3>
                <div style="overflow-x: auto;">
                    <table>
                        <thead><tr><th>source_file</th><th>issue_type</th><th>detail</th></tr></thead>
                        <tbody>{_render_chunking_details(cat)}</tbody>
                    </table>
                </div>
            </section>
        """)

    if "edge_cases" in by_name:
        cat = by_name["edge_cases"]
        sub = cat.metrics.get("subcategories", {})
        sub_rows = "".join(
            f"<tr><td>{escape(name)}</td><td>{data.get('passed', 0)}/{data.get('total', 0)}</td><td>{data.get('pass_rate', 0):.0%}</td></tr>"
            for name, data in sub.items()
        )
        sections.append(f"""
            <section class="panel">
                <h2>4. Edge Cases — ציון {cat.score:.1f}</h2>
                <p class="muted">המדד הזה הוא תערובת של בדיקות דטרמיניסטיות והרצה מחדש של הסוכן. הקוד ב-<code>src/eval_edge_cases.py</code> מפעיל את המערכת שוב על שאלות <code>no_answer</code>, <code>cross_protocol</code>, <code>specificity</code> ו-<code>ambiguous</code>, ואז בודק heuristics כמו אורך תשובה, סירוב לענות, מספרים בתשובה, ושליפה ממספר מסמכים.</p>
                <div class="metrics-list">{_render_metrics_block(cat.metrics)}</div>
                {_render_explanation_list([
                    "<strong>no_answer</strong> — עובר רק אם המערכת מסרבת לענות, נשארת קצרה, ולא ממציאה מספרים.",
                    "<strong>cross_protocol</strong> — עובר רק אם נשלפו לפחות שני קבצי מקור שונים, התשובה לא מסרבת, ויש מספיק אורך כדי לרמוז על סינתזה.",
                    "<strong>specificity</strong> — בודק האם מספרים ומילות מפתח מה-<code>golden_answer</code> מופיעים בתשובה בפועל.",
                    "<strong>ambiguous</strong> — בודק אם המערכת מבקשת הבהרה, מסתייגת, או לפחות נשארת כללית וקצרה בלי מספרים מיותרים.",
                ])}
                <h3>פירוט לפי תת-קטגוריה</h3>
                <table>
                    <thead><tr><th>subcategory</th><th>passed/total</th><th>pass_rate</th></tr></thead>
                    <tbody>{sub_rows}</tbody>
                </table>
            </section>
        """)

    sections.append(f"""
        <section class="panel">
            <h2>5. Consolidated Review Queue</h2>
            <p class="muted">במקום להציג את אותן שאלות שוב ושוב בכל קטגוריה, הטבלה הבאה מרכזת רק שאלות שדורשות קריאה נוספת: כשלי שליפה, ציוני שופט לא מושלמים, או כשלי edge-case.</p>
            {_render_question_review_queue(report, eval_set)}
        </section>
    """)

    extra_css = """
        .overall-banner { display: inline-block; margin-top: 12px; padding: 12px 18px; border: 2px solid; border-radius: 8px; }
        .overall-number { font-size: 38px; font-weight: 700; line-height: 1; }
        .metrics-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 6px 18px; margin-bottom: 12px; }
        .metric-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #e4e7eb; }
        .metric-name { font-weight: 600; }
        .metric-value { font-family: monospace; }
        .issue-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin: 14px 0; }
        .issue-card { border: 1px solid #d9e2ec; border-radius: 8px; padding: 14px; background: #f8fafc; }
        h2 { margin-top: 0; }
        h3 { margin-top: 18px; }
    """
    return _html_doc("Protokal.AI — Technical Report", "".join(sections), extra_css)


# ---------------------------------------------------------------------------
# 3. Client Summary Report  (דוח מסכם ללקוח)
# ---------------------------------------------------------------------------

def render_client_summary_report(report: EvalReport, eval_set: EvalSet) -> str:
    """Top-level executive summary: one big number + 4 business KPIs."""

    by_name = _category_by_name(report)
    overall_status = _score_status(report.overall_score)
    overall_color = _status_color(overall_status)

    cards = []
    # Order matches the task spec: Answer → Retrieval → Edge → Chunking
    for cat_name in ("answer", "retrieval", "edge_cases", "chunking"):
        cat = by_name.get(cat_name)
        kpi = BUSINESS_KPI[cat_name]
        if not cat:
            continue
        weight = CATEGORY_WEIGHTS[cat_name]
        color = _status_color(cat.status)
        cards.append(f"""
            <article class="kpi-card" style="border-color: {color};">
                <div class="kpi-head">
                    <h3>{escape(kpi['title'])}</h3>
                    <div class="kpi-sub">{escape(kpi['subtitle'])}</div>
                </div>
                <div class="kpi-score" style="color: {color};">{cat.score:.0f}<span class="kpi-unit">/100</span></div>
                <div class="kpi-meta">
                    <span class="chip chip-{ {'pass':'ok','warn':'warn','fail':'danger'}.get(cat.status,'ok') }">{escape(_status_label(cat.status))}</span>
                    <span class="chip">משקל בציון הכולל: {weight:.0%}</span>
                </div>
                <p class="kpi-explain">{escape(kpi['explain'])}</p>
            </article>
        """)

    body = f"""
        <section class="hero">
            <h1>דוח מסכם ללקוח</h1>
            <p class="muted">תמונת מצב כללית של איכות מערכת ה-RAG, בארבעה מדדי-על עסקיים.</p>
        </section>

        <section class="panel overall-panel" style="border-color: {overall_color};">
            <div class="overall-grid">
                <div>
                    <div class="overall-label">ציון איכות המערכת הכולל</div>
                    <div class="overall-explain">משקלל את ארבעת מדדי-העל לפי החשיבות העסקית של כל אחד.</div>
                </div>
                <div class="overall-number-box" style="color: {overall_color};">
                    <div class="overall-number">{report.overall_score:.0f}<span class="kpi-unit">%</span></div>
                    <div class="overall-status">{escape(_status_label(overall_status))}</div>
                </div>
            </div>
        </section>

        <section class="kpi-grid">
            {''.join(cards)}
        </section>

        <section class="panel">
            <h2>איך לקרוא את הדוח</h2>
            <ul>
                <li><strong>ציון 80 ומעלה</strong> — המערכת עובדת היטב באזור הזה.</li>
                <li><strong>60–79</strong> — דורש תשומת לב; מומלץ לבדוק עם הצוות הטכני.</li>
                <li><strong>מתחת ל-60</strong> — דורש תיקון לפני שימוש מבצעי.</li>
            </ul>
            <p class="muted">לפירוט מלא ראו את הדוח הטכני. לפעולות שדרושות לשיפור הבנצ'מרק עצמו ראו את דוח העבודה ללקוח.</p>
        </section>
    """

    extra_css = """
        .overall-panel { border-width: 2px; }
        .overall-grid { display: grid; grid-template-columns: 1.6fr 1fr; gap: 20px; align-items: center; }
        .overall-label { font-size: 22px; font-weight: 700; margin-bottom: 6px; }
        .overall-explain { color: #52606d; }
        .overall-number-box { text-align: center; }
        .overall-number { font-size: 84px; font-weight: 700; line-height: 1; }
        .overall-status { margin-top: 6px; font-size: 16px; font-weight: 600; }
        .kpi-grid { display: grid; grid-template-columns: repeat(2, minmax(320px, 1fr)); gap: 20px; margin-bottom: 24px; }
        .kpi-card { background: white; border: 2px solid; border-radius: 10px; padding: 22px; }
        .kpi-head h3 { margin: 0; font-size: 22px; }
        .kpi-sub { color: #52606d; font-size: 13px; margin-bottom: 10px; }
        .kpi-score { font-size: 64px; font-weight: 700; line-height: 1; margin-top: 8px; }
        .kpi-unit { font-size: 22px; font-weight: 600; color: #52606d; margin-right: 4px; }
        .kpi-meta { margin-top: 10px; }
        .kpi-explain { margin-top: 14px; color: #1f2933; }
        @media (max-width: 980px) {
            .overall-grid, .kpi-grid { grid-template-columns: 1fr; }
            .overall-number { font-size: 64px; }
        }
    """
    return _html_doc("Protokal.AI — Client Summary Report", body, extra_css)


# ---------------------------------------------------------------------------
# Public façade — write all three reports to disk
# ---------------------------------------------------------------------------

def write_all_reports(
    report: EvalReport,
    eval_set: EvalSet,
    *,
    client_work_path: str,
    technical_path: str,
    client_summary_path: str,
) -> None:
    """Generate the three reports without re-running evaluation."""

    pairs = [
        (client_work_path, render_client_work_report(report, eval_set)),
        (technical_path, render_technical_report(report, eval_set)),
        (client_summary_path, render_client_summary_report(report, eval_set)),
    ]
    for path, html in pairs:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
