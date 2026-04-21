# AI Agent Coordination

Last updated: 2026-04-21
Repository: `C:\Users\CCSV\Desktop\Projects\protokal\retrieval`

## Purpose

This repository is worked on by multiple AI agents and tools, including Codex, Cursor, Claude Code, Anti Gravity, and others.

This file is the shared coordination layer for all agents. It exists to keep the overall plan clear, avoid duplicated work, and make handoff between agents reliable.

## What Every Agent Must Do

Every agent that starts work in this repository should read this file first.

Every agent that finishes work must update this file before stopping.

Status updates must be written only in `Current Active Stage`.

The status entry must stay minimal and include only:

1. Commit hash
2. Agent name
3. One short line describing what was done
4. A single line starting with `-` that marks the exact current place or next place in the workflow

Do not write a long handoff log here.

Do not duplicate status updates in other sections.

The reason for this rule is to save tokens and avoid unnecessary context for the next agent.

If an agent has deeper notes, they should keep them brief and only include them when truly necessary.

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

## Working Direction

This project currently has two main tracks.

### Track 1: Build a High-Quality `_QUESTIONS` Source of Truth

The benchmark is only as good as the question bank.

If the questions, golden answers, and expected source references are weak or inaccurate, evaluation results are not trustworthy and it is hard to know whether the RAG system improved.

### Track 2: Make the Evaluation Suite Reliable

Even with a strong `_QUESTIONS` bank, the evaluation system itself must be operationally stable and logically correct.

The suite should clearly measure:

- Retrieval quality
- Answer quality
- Chunking quality
- Edge-case behavior

## Current Strategic Plan

### Phase 1: Understand and Validate the Existing Evaluation Code

Immediate goal:

1. Learn the current testing and evaluation code deeply
2. Verify that all required pieces are present
3. Prove the current system runs end-to-end in a controlled way
4. Stabilize the data contract between `_QUESTIONS`, `eval_set.json`, and `run_eval.py`

### Phase 2: Design a Human-in-the-Loop Update Flow for `_QUESTIONS`

Target direction:

- Real user questions should feed the benchmark over time
- A human reviewer should see the question and the current stored answer
- The reviewer should correct the answer and supporting metadata if needed
- The corrected version should become part of the maintained benchmark

Preferred design direction:

- Separate raw user questions from reviewed benchmark questions
- Keep review metadata in structured data
- Prefer structured benchmark storage over direct UI editing of Python source

## Current Active Stage

Commit: `04f68a9`
Agent: `Codex`
Status: fixed evaluator metadata parsing, corrected retrieval score scaling, and tightened cross-protocol edge-case checks
- Next: review broad-question retrieval expectations and improve the remaining edge-case heuristics where the logic is still too coarse
