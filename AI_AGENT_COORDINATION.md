# AI Agent Coordination

Last updated: 2026-04-21
Repository: `C:\Users\CCSV\Desktop\Projects\protokal\retrieval`

## Purpose

This repository is actively worked on by multiple AI coding agents and tools, including Codex, Cursor, Claude Code, Anti Gravity, and others.

This file is the shared coordination layer for all agents working on this project. Its job is to keep the overall plan clear, reduce duplicated work, preserve context between sessions, and make handoffs reliable.

## What Every Agent Must Do

Every agent that starts work in this repository should read this file first.

Every agent that completes a task must update this file before finishing. The update must include:

1. What task was attempted
2. What was completed
3. What remains open
4. Any risks, blockers, or caveats
5. Notes for the next agent if needed

Do not silently finish work without updating this file.

Do not overwrite previous handoff notes unless they are clearly obsolete. Prefer appending dated entries to the handoff log.

If you start a task and do not finish it, update the status here anyway so the next agent understands the current state.

## Project Overview

This project is a retrieval and RAG evaluation system over committee protocol documents.

Core capabilities in the current codebase:

- Retrieve relevant chunks from a Firestore-backed vector store
- Use Vertex AI / Gemini models for embeddings and answer generation
- Run a one-question smoke test through the RAG pipeline
- Build an evaluation set from `_QUESTIONS` in `build_eval.py`
- Run multiple evaluation modules from `run_eval.py`
- Score retrieval quality, answer quality, chunking quality, and edge cases

Main repository files:

- `main.py`: simple smoke test for one retrieval question
- `build_eval.py`: source question bank and eval-set builder
- `run_eval.py`: orchestrates the full evaluation run and dashboard/report generation
- `src/eval_retrieval.py`: retrieval metrics
- `src/eval_answer.py`: LLM-as-judge answer scoring
- `src/eval_chunking.py`: chunking quality evaluation
- `src/eval_edge_cases.py`: no-answer / ambiguous / edge behavior checks
- `src/judge.py`: judge model behavior
- `src/models.py`: shared pydantic models for reports and items

## Current Product Direction

The project currently has two main evaluation tracks.

### Track 1: Build a High-Quality `_QUESTIONS` Source of Truth

The benchmark is only as good as the question bank.

If the questions, golden answers, and expected source references are weak or inaccurate, we cannot trust the evaluation results and we cannot tell whether the RAG system is improving.

Current direction:

- Keep the category structure
- Improve the quality of questions and golden answers
- Improve `expected_source_files`
- Use this file and future tooling to coordinate how the question bank evolves

### Track 2: Make the Evaluation Suite Itself Reliable

Even with a strong `_QUESTIONS` bank, the evaluation system must be operationally solid and logically correct.

We need to verify:

- The code path is complete
- The evaluation modules measure what we think they measure
- The evaluation run is stable enough to use regularly
- Failure modes are understood clearly
- Reports are useful for deciding whether the RAG improved

## Current Strategic Plan

### Phase 1: Understand and Validate the Existing Evaluation Code

Immediate goal:

1. Learn the current testing and evaluation code deeply
2. Verify that all required pieces are present
3. Prove the current system runs end-to-end in a controlled way
4. Document what works, what is brittle, and what is misleading

This phase should focus on the current implementation before adding new product mechanisms.

### Phase 2: Design a Human-in-the-Loop Update Flow for `_QUESTIONS`

Target direction:

- Real user questions should feed the benchmark over time
- A human reviewer should see the question and the current stored answer
- The reviewer should be able to correct the answer and supporting metadata if needed
- The corrected version should become part of the maintained benchmark

Recommended design direction:

- Treat raw user questions and reviewed benchmark questions as different states
- Keep review metadata such as source, review status, reviewer, and last reviewed time
- Prefer storing editable question data in a structured data file rather than editing Python source directly through the review UI
- Generate or sync `_QUESTIONS` from structured reviewed data when appropriate

## Working Rules For Benchmark Evolution

When adding or editing benchmark items, prefer fields such as:

- `question`
- `category`
- `golden_answer`
- `expected_source_files`
- `expected_section_types`
- `source`
- `status`
- `last_reviewed_at`
- `review_notes`

Suggested lifecycle:

1. New question enters as draft
2. Human reviewer validates or corrects it
3. Reviewed item becomes approved benchmark content
4. Evaluation suite uses approved items for comparison

## Current Status Snapshot

### Git / Repo Status

- Branch: `main`
- Recent pushed commits from this session:
  - `a961bd2` - `Expand retrieval eval question set`
  - `4598efc` - `Add multi-agent coordination guide`

### What Was Already Verified In This Session

- `main.py` smoke test ran successfully against the live retrieval pipeline
- `Round 1` broad questions ran successfully
- `Round 2` specific questions mostly looked good, with a notable mismatch around the Carol Sadeh question
- `Round 3` no-answer behavior looked good; one run hit a temporary Vertex AI `429 RESOURCE_EXHAUSTED`, then succeeded after waiting and retrying
- `Round 4` cross-protocol questions exposed a harder quality problem:
  - Question 1 on gardening decisions looked reasonably good
  - Question 2 on budget evolution returned relevant information, but did not truly answer the cross-meeting historical trend

### Current Interpretation

- The system is operational
- Specific fact-based questions are currently much stronger than cross-protocol synthesis questions
- No-answer handling looks promising
- The benchmark itself is becoming better, but still needs careful human review to become a trustworthy ground truth

## Current Active Stage

Active stage as of 2026-04-21:

`Phase 1 - audit the current evaluation code deeply, verify completeness, and document how to make it reliable`

## Notes To The Next Agent

- Read the evaluation flow before changing benchmark design
- Be careful not to confuse operational success with evaluation quality
- Cross-protocol questions are a known weak area and should be examined closely
- If you make progress, update this file before you stop

## Handoff Log

### 2026-04-21 - Coordination File Created

Agent: Codex

Completed:

- Added this coordination file at repo root
- Documented the current multi-agent workflow and shared expectations
- Recorded the current project direction and working assumptions
- Recorded the latest known evaluation observations from this session

Open:

- Full audit of the evaluation code is still in progress
- Reliability review of the evaluation modules has not yet been written up
- Human-in-the-loop benchmark update design has not yet been implemented

Notes for next agent:

- Continue with Phase 1 before building new UI or new benchmark infrastructure
- Update this file again after each meaningful milestone

### 2026-04-21 - Evaluation Audit And Controlled Run

Agent: Codex

Completed:

- Mapped the current evaluation flow from `_QUESTIONS` in `build_eval.py` to `eval_set.json`, then into `run_eval.py`, then into the four evaluator modules
- Read and reviewed the main evaluation components:
  - `run_eval.py`
  - `src/models.py`
  - `src/eval_retrieval.py`
  - `src/eval_answer.py`
  - `src/eval_chunking.py`
  - `src/eval_edge_cases.py`
  - `src/agent.py`
  - `src/retriever.py`
  - `src/judge.py`
  - `src/dashboard.py`
- Verified that `run_eval.main()` can execute end-to-end when the browser open call is neutralized
- Verified that the current run produced `eval_report.json` and `eval_dashboard.html`
- Verified that `_QUESTIONS` currently contains 53 items
- Verified that the checked-in `eval_set.json` is still version `1.0` with only `10` items

Key findings:

- The current `run_eval.py` does not rebuild `eval_set.json` before evaluation
- The current `eval_set.json` is stale relative to `_QUESTIONS`
- Because the current `eval_set.json` lacks the richer metadata expected by the newer evaluators, the controlled `run_eval` execution produced:
  - Retrieval evaluation on `0/10` scorable items
  - Edge-case evaluation on `0/10` scorable items
  - Answer completeness average `0.0`
- `AnswerEvaluator` judges `item.answer` from `eval_set.json`, not necessarily a fresh answer generated during the current run
- This means the current answer-quality score can drift away from the live system if `eval_set.json` is not rebuilt immediately before evaluation
- `EdgeCaseEvaluator` currently uses lightweight heuristics:
  - `cross_protocol` only checks whether retrieval returned multiple source files
  - `ambiguous` mostly checks for short or caveated answers, not true hallucination control
  - `no_answer` checks refusal behavior, but not retrieval quality
- `ChunkingEvaluator` is the most operationally complete module right now; the controlled run returned a pass with 667 chunks, 116 files, and 13 issues
- `run_eval.py` ends by opening a browser, which is not ideal for automation or headless usage

Controlled run summary:

- `run_eval.py` completed successfully in a controlled invocation
- Overall score from that run was not trustworthy as a product signal because it was computed over a stale `eval_set.json`
- The run still proved that the current orchestration path is functional

Open:

- Decide what the source of truth is between `_QUESTIONS` and `eval_set.json`
- Decide whether `run_eval.py` should:
  - always rebuild a fresh eval set first
  - fail if `eval_set.json` is stale
  - or generate fresh live answers during evaluation instead of relying on stored answers
- Tighten the edge-case scoring logic so it measures actual behavior quality, not only coarse heuristics

Notes for next agent:

- Do not trust the current overall score from `run_eval.py` until the freshness contract between `_QUESTIONS`, `eval_set.json`, and the evaluators is fixed
- The first architectural issue to solve is the data contract, not the dashboard
