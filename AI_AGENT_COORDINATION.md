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

Top-level layout:

- `main.py` — orchestration entry point and one-question smoke test
- `create_index.py` — one-off Firestore vector-index creation utility
- `retrieval/` — core: `settings.py`, `logger.py`, `request_guard.py`, `retriever.py`, `agent.py`, `models.py`
- `app/` — FastAPI service (`api.py`) and static UI (`public/index.html`)
- `evaluation/` — eval suite: `models.py`, `judge.py`, `build_eval.py`, `run_eval.py`, `eval_*.py`, `dashboard.py`, `reports.py`, `generate_reports.py`

## Current Task List

_All tracked tasks are complete. Add the next initiative here._

## Current Active Stage

- `[Archived History]` | April 21-26, 2026 | Various Agents | Built and tuned evaluation pipelines, stabilized retrieval and edge-case heuristics, implemented the `RequestGuard`, generated technical and client-facing HTML reports.
- `2026-04-27 00:00:00 -0700` | `54e58a4` | `Codex` | aligned the split reports with client feedback by fixing the executive status label, removing the client-work action column, and replacing repeated technical tables with methodology + a consolidated review queue
- `2026-04-27 02:50:00 -0700` | `uncommitted` | `Antigravity` | injected document metadata into RAG prompts, enforced Hebrew citation outputs from the LLM, and exposed the pipeline over a new FastAPI service (`src/api.py`) with a minimalistic HTML/JS UI (`public/index.html`).
- `2026-04-27 05:45:00 -0700` | `uncommitted` | `Antigravity` | Extracted nested Firestore metadata to correctly display source filenames and added clickable Google Cloud Storage links to the UI source cards.
- `2026-04-27 06:55:00 -0700` | `uncommitted` | `Claude` | Split the monolithic `src/` into three packages — `retrieval/` (core RAG + DB), `app/` (FastAPI + static UI), `evaluation/` (eval suite). Models split into `retrieval/models.py` and `evaluation/models.py`; all imports rewritten; `app/api.py` resolves the static dir from its own location; `main.py serve` now points at `app.api:app`. Smoke test through `main.py` passes.
- Current place: Restructure complete. Awaiting next task from product owner.
