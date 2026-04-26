# AI Agent Coordination

Last updated: 2026-04-23
Repository: `C:\Users\CCSV\Desktop\Projects\protokal\retrieval`

## Purpose

This repository is worked on by multiple AI agents and tools, including Codex, Cursor, Claude Code, Anti Gravity, and others.

This file is the shared coordination layer for all agents. It exists to keep the overall plan clear, avoid duplicated work, and make handoff between agents reliable.

## What Every Agent Must Do

Every agent that starts work in this repository should read this file first.

Every agent should understand both the project and the current remaining task list before starting work.

Every agent that finishes work must update this file before stopping.

The file should be maintained in two different ways:

1. `Current Task List` is dynamic and must contain only the work that still remains from the current point in time
2. `Current Active Stage` is the running history log of what agents already did

When an agent completes a task, it should delete that completed work from `Current Task List`.

If new tasks are discovered, changed, split, merged, or removed, the agent should update `Current Task List` so it always reflects only the forward-looking plan.

When an agent finishes work, it should add a short entry to `Current Active Stage` with:

1. Time
2. Commit hash
3. Agent name
4. One short line describing what was done
5. One line starting with `-` that marks the exact current place or next place in the workflow

The goal is:

- `Current Task List` = only what still needs to be done
- `Current Active Stage` = the compact historical log of agent work on the project

Do not keep history inside `Current Task List`.

## Project Overview

This project is a retrieval and RAG evaluation system over committee protocol documents.

Current core capabilities:

- Retrieve relevant chunks from a Firestore-backed vector store
- Use Vertex AI / Gemini models for embeddings and answer generation
- Run a one-question smoke test through the RAG pipeline
- Build an evaluation set from `_QUESTIONS` in `build_eval.py`
- Run evaluation modules from `run_eval.py`
- Score retrieval quality, answer quality, chunking quality, and edge cases

Main files:

- `main.py`
- `build_eval.py`
- `run_eval.py`
- `src/eval_retrieval.py`
- `src/eval_answer.py`
- `src/eval_chunking.py`
- `src/eval_edge_cases.py`
- `src/judge.py`
- `src/models.py`

## Current Task List

1. Capture the first full baseline on all 53 current questions.
Run `run_eval.py` without `PROTOKAL_SAMPLE_PER_CATEGORY` so the system rebuilds `eval_set.json` from the full `_QUESTIONS` bank and produces fresh `eval_report.json` / `eval_dashboard.html`.
Do not change scoring logic during this baseline capture.
After the run completes, record the final overall score and the four category scores in this coordination file.

2. Turn the latest smoke-run result into an explicit scoring work queue before changing code.
The latest representative smoke run already completed successfully on 12 questions and exposed the main weak area: `edge_cases` failed at 37.5.
Break the follow-up work into these three sub-problems:
- `no_answer`: the system still answers too much or includes too many concrete details when it should refuse.
- `ambiguous`: the system gives overly specific answers instead of caveating, asking for clarification, or staying high-level.
- `cross_protocol`: one sampled question still failed because the answer behavior did not match the intended multi-protocol synthesis test.
Before editing heuristics or prompts, confirm for each failure whether the problem is in product behavior, evaluator logic, or benchmark definition.

3. Finish hardening the long-running evaluation flow against Vertex AI 429 failures across all stages.
The original retry/resume work fixed `build_eval.py` only, but later logs showed that `answer` evaluation could still die inside `JudgeAgent`.
A shared `RequestGuard` has now been added and wired through retriever, answer generation, and judge calls.
The next verification step is a successful full 53-question run without manual restarts beyond the existing `eval_set.json` resume behavior.
If failures still occur after the shared guard, the next likely enhancement is checkpoint/resume for category-level evaluation, not only eval-set generation.

4. After each scoring or prompt change, run a representative smoke slice again and compare it against the current baseline.
Use `PROTOKAL_SAMPLE_PER_CATEGORY=2` unless a different slice is explicitly needed.
Check that scores stay on a sane 0-100 scale, that the intended failure mode improves, and that the dashboard still explains the fresh outputs clearly.
Do not rely only on one full run at the end.

5. Tighten the question-bank contract only when an evaluation issue reveals a concrete benchmark mismatch.
Review `_QUESTIONS` for category fit, `golden_answer` quality, and retrieval expectations whenever a scoring problem suggests the benchmark itself is underspecified.
The recent wording cleanup in `build_eval.py` was intentionally small and local; continue in that style only when a concrete mismatch is found.

6. Design the next structure for human-in-the-loop `_QUESTIONS` maintenance after the scoring flow is stable enough.
The long-term benchmark should support real user questions, human correction, and review metadata.
The source of truth should be structured and reviewable, not only handwritten Python.

7. Split the evaluation results into three distinct reports without requiring a re-run.
The current `eval_dashboard.html` produces a single view that is not clear enough. We need to parse the existing results (e.g., from `eval_report.json`) and generate three separate reports:
- **Client Work Report (דוח עבודה ללקוח)**: Contains the table of questions, gold answers, categories, and other relevant information. This report must include an explanation for the client regarding the importance of this file and what actions they need to take.
- **Technical Report (דוח טכני)**: For data scientists and statisticians. This is the most detailed technical report showing everything that happened between questions and answers, all metrics, and how everything connects to the final score.
- **Client Summary Report (דוח מסכם ללקוח)**: Presents only the final picture to the client. Must include:
  - Total System Score (ציון איכות המערכת הכולל): A weighted score from 0 to 100%.
  - Breakdown into 4 core metrics with business titles:
    - Final Answer Quality (איכות התשובות הסופיות) [% of score]: Are the system's answers complete, accurate, and free of "hallucinations" (measured against gold answers).
    - Information Retrieval Ability (יכולת איתור המידע) [% of score]: Does the system successfully retrieve the correct documents and paragraphs from the database before answering.
    - Reliability in Edge Cases (אמינות במצבי קיצון) [% of score]: Does the system know to say "I don't know" when info is missing, and does it correctly handle complex questions that cross-reference multiple protocols.
    - Database Integrity (תקינות בסיס הנתונים) [% of score]: Technical metric reflecting the quality of file arrangement and their slicing in the backend system.
*Important requirement*: Do not execute another evaluation run to get this data. Extract it from the existing JSON outputs. The code implementation must be elegant and clean, not a hacked patch.

## Current Active Stage

- `2026-04-21 00:33:19 -0700` | `a961bd2` | `Codex` | expanded the retrieval eval question bank with more grounded questions and metadata
- `2026-04-21 01:30:29 -0700` | `Codex` | `4598efc` | added the first shared multi-agent coordination file
- `2026-04-21 01:45:51 -0700` | `Codex` | `62fab87` | documented the evaluation audit findings after the first controlled run
- `2026-04-21 01:52:32 -0700` | `Codex` | `5bb79fe` | simplified coordination status updates to the leaner format
- `2026-04-21 01:56:12 -0700` | `Codex` | `5822818` | stabilized the eval data contract so `run_eval.py` rebuilds a fresh eval set before scoring
- `2026-04-21 01:56:23 -0700` | `Codex` | `5c0353f` | updated the coordination file after the eval-set rebuild fix
- `2026-04-21 02:01:47 -0700` | `Codex` | `04f68a9` | fixed evaluator metadata parsing, corrected retrieval score scaling, and tightened cross-protocol edge-case checks
- `2026-04-21 02:01:59 -0700` | `Codex` | `990e5bb` | updated the coordination file after the evaluator fixes
- `2026-04-21 02:52:51 -0700` | `Codex` | `eaad35d` | tuned broad-question retrieval scoring and tightened `no_answer`, `cross_protocol`, and `ambiguous` heuristics with targeted smoke checks
- `2026-04-21 02:57:10 -0700` | `Antigravity` | `6fd7182` | tuned broad/cross_protocol retrieval section-type expectations; tightened no_answer (≤180 chars, ≤1 number) and ambiguous (added _CAVEAT_RE, ≤150 chars, 0 numbers) heuristics
- `2026-04-21 03:12:06 -0700` | `Antigravity` | `71c8507` | codebase audit complete — all 15 files syntax-checked, create_index.py wrapped in main(), .gitignore extended to exclude generated outputs and scratch files, eval_set.json untracked
- `2026-04-21 15:40:00 +0300` | `manual` | `Human` | reprioritized tasks: pause scoring changes, establish baseline with full evaluation cycle, and implement dashboard infrastructure
- `2026-04-22 07:35:00 +0300` | `uncommitted` | `Claude Code` | added `sample_per_category(n)` helper to `build_eval.py` and wired `PROTOKAL_SAMPLE_PER_CATEGORY` env var into `run_eval.py` to support low-cost smoke runs; verified end-to-end pipeline on a 12-question sample (2 per category) — generated `eval_report.json` and `eval_dashboard.html` for the first time. Sample results: overall 76.7/100, retrieval 76.2 (pass), answer 92.5 (pass), chunking 93.1 (pass), edge_cases 37.5 (fail — ambiguous 0/2 and no_answer 0/2 are the regressions; cross_protocol 2/2, specificity 1/2). No scoring changes were made.
- `2026-04-23 04:49:24 -0700` | `uncommitted` | `Codex` | rewrote `src/dashboard.py` into a client-facing work document that explains the tests, ties table fields to metrics, and turns the question grid into a collaborative benchmark worksheet
- `2026-04-23 05:24:20 -0700` | `uncommitted` | `Codex` | validated the redesigned dashboard on a fresh 12-question smoke run and lightly tightened several benchmark question wordings in `build_eval.py`
- `2026-04-24 07:10:18 -0700` | `uncommitted` | `Codex` | replaced stage-specific 429 handling with a shared `RequestGuard` across retriever, generator, and judge calls; kept eval-set resume and verified the new guard on a 6-question smoke run that recovered from a real 429 during completeness scoring
- `2026-04-26 04:30:00 -0700` | `uncommitted` | `Antigravity` | added task to split evaluation results into three distinct reports (Client Work, Technical, Client Summary) without re-running evaluation.
- Current place: added new reporting requirements to the task list. Next: implement the report generation logic to create the three new reports from existing evaluation outputs.
