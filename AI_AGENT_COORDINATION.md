# AI Agent Coordination

Last updated: 2026-04-21
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

1. Establish current baseline and implement dashboard.
Do not change the scoring mechanism yet. First, close the full evaluation cycle using the *existing* scoring rules. Implement and connect the existing dashboard infrastructure so we can get a clear snapshot of the system's answer quality as it is right now. 

2. Run controlled representative eval slices after each scoring change. (Start only after Task 1 is complete).
Use a small set of broad, specific, no-answer, cross-protocol, and specificity questions.
Verify that scores stay on a sane 0-100 scale and that the outputs reflect real system behavior.
Do not rely only on one full run at the end.

3. Design the next structure for human-in-the-loop `_QUESTIONS` maintenance.
The long-term benchmark should support real user questions, human correction, and review metadata.
The source of truth should be structured and reviewable, not only handwritten Python.
Prepare the design after the current evaluation code is stable enough.

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
- Current place: task 1 in `Current Task List` — run full evaluation with existing scoring and connect the dashboard