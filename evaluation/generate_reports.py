"""Build the three split reports from existing eval_report.json + eval_set.json.

This entry point does NOT run any evaluation. It only reads the JSON outputs
produced by run_eval.py and renders three separate HTML files:

  - client_work_report.html      (דוח עבודה ללקוח)
  - technical_report.html        (דוח טכני)
  - client_summary_report.html   (דוח מסכם ללקוח)

Usage:
    python generate_reports.py
    python generate_reports.py --report eval_report.json --eval-set eval_set.json
"""

import argparse
import json
import os
import sys
import webbrowser

from evaluation.models import EvalReport, EvalSet
from evaluation.reports import write_all_reports


def _load_eval_set(path: str) -> EvalSet:
    with open(path, "r", encoding="utf-8") as f:
        return EvalSet(**json.load(f))


def _load_eval_report(path: str) -> EvalReport:
    with open(path, "r", encoding="utf-8") as f:
        return EvalReport(**json.load(f))


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Generate the three split RAG-evaluation reports from existing JSON outputs.")
    parser.add_argument("--report", default="eval_report.json", help="Path to eval_report.json")
    parser.add_argument("--eval-set", default="eval_set.json", help="Path to eval_set.json")
    parser.add_argument("--client-work", default="client_work_report.html")
    parser.add_argument("--technical", default="technical_report.html")
    parser.add_argument("--summary", default="client_summary_report.html")
    parser.add_argument("--open", action="store_true", help="Open the summary report in a browser when done.")
    args = parser.parse_args()

    if not os.path.exists(args.report):
        raise FileNotFoundError(f"Eval report not found: {args.report}. Run run_eval.py first.")
    if not os.path.exists(args.eval_set):
        raise FileNotFoundError(f"Eval set not found: {args.eval_set}. Run run_eval.py first.")

    report = _load_eval_report(args.report)
    eval_set = _load_eval_set(args.eval_set)

    write_all_reports(
        report,
        eval_set,
        client_work_path=args.client_work,
        technical_path=args.technical,
        client_summary_path=args.summary,
    )

    print("Generated reports:")
    print(f"  Client Work    : {args.client_work}")
    print(f"  Technical      : {args.technical}")
    print(f"  Client Summary : {args.summary}")

    if args.open:
        webbrowser.open(os.path.abspath(args.summary))


if __name__ == "__main__":
    main()
