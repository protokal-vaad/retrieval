from pydantic import BaseModel, Field
from typing import List, Optional


class Document(BaseModel):
    """Represents a single retrieved document chunk from Firestore."""

    content: str = Field(..., description="Text content of the document chunk")
    metadata: dict = Field(default_factory=dict, description="Document metadata (source, page, etc.)")


class RetrievalResult(BaseModel):
    """Full result returned by the RAG agent for a given query."""

    question: str = Field(..., description="The original user question")
    answer: str = Field(..., description="The LLM-generated answer")
    source_documents: List[Document] = Field(
        default_factory=list, description="Retrieved documents used as context"
    )


class EvalItem(BaseModel):
    """A single Q&A pair in the evaluation set."""

    id: int = Field(..., description="Sequential identifier (1-based)")
    round: int = Field(..., description="1=broad exploratory, 2=specific follow-up")
    category: str = Field(
        default="broad",
        description="Question category: broad, specific, no_answer, cross_protocol, specificity, ambiguous",
    )
    question: str = Field(..., description="Hebrew question posed to the RAG system")
    answer: str = Field(default="", description="RAG system answer — baseline for regression")
    golden_answer: Optional[str] = Field(
        default=None, description="Manually verified correct answer for completeness scoring"
    )
    expected_source_files: List[str] = Field(
        default_factory=list, description="Source filenames that should appear in retrieval results"
    )
    expected_section_types: List[str] = Field(
        default_factory=list, description="Expected section types: Header and Agenda, Topic Discussion, Closing and Decisions"
    )
    num_sources: int = Field(default=0, description="Number of retrieved source documents")
    source_previews: List[str] = Field(default_factory=list, description="First 120 chars of each source")


class EvalSet(BaseModel):
    """Complete evaluation set saved to eval_set.json."""

    version: str = Field(default="2.0", description="Schema version")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp of build time")
    total_items: int = Field(..., description="Total Q&A pairs")
    items: List[EvalItem] = Field(..., description="Ordered evaluation items")


# ---------------------------------------------------------------------------
# Scoring models — used by eval modules and the dashboard
# ---------------------------------------------------------------------------

class JudgeScore(BaseModel):
    """Single LLM-as-Judge score for one dimension."""

    score: int = Field(..., ge=1, le=5, description="Score from 1 (worst) to 5 (best)")
    reasoning: str = Field(..., description="Judge explanation for the score")


class CompletenessScore(BaseModel):
    """LLM-as-Judge completeness score comparing RAG answer to golden answer."""

    score: int = Field(..., ge=1, le=5, description="Score from 1 (worst) to 5 (best)")
    missing_facts: List[str] = Field(default_factory=list, description="Key facts present in golden answer but missing from RAG answer")


class AnswerScore(BaseModel):
    """Combined answer quality scores for a single question."""

    question_id: int = Field(..., description="Links back to EvalItem.id")
    faithfulness: JudgeScore = Field(..., description="Does the answer stick to the context?")
    relevance: JudgeScore = Field(..., description="Does the answer address the question?")
    completeness: Optional[CompletenessScore] = Field(
        default=None, description="Only scored when a golden_answer exists"
    )


class RetrievalScore(BaseModel):
    """Retrieval quality scores for a single question."""

    question_id: int = Field(..., description="Links back to EvalItem.id")
    hit: bool = Field(..., description="At least one retrieved chunk matches expected sources")
    reciprocal_rank: float = Field(..., description="1/position of first relevant chunk (0 if none)")
    precision: float = Field(..., description="Fraction of retrieved chunks that are relevant")


class ChunkingIssue(BaseModel):
    """A single chunking quality problem found in Firestore data."""

    source_file: str = Field(..., description="The document file where the issue was found")
    issue_type: str = Field(..., description="missing_metadata | bad_section_dist | encoding_error | bad_chunk_count | empty_content")
    detail: str = Field(..., description="Human-readable description of the issue")


class EdgeCaseResult(BaseModel):
    """Eval result for a single edge-case question."""

    question_id: int = Field(..., description="Links back to EvalItem.id")
    category: str = Field(..., description="no_answer | cross_protocol | specificity | ambiguous")
    passed: bool = Field(..., description="Whether the system handled this case correctly")
    detail: str = Field(..., description="Explanation of pass/fail")


class CategoryReport(BaseModel):
    """Aggregated scores for one eval category."""

    category: str = Field(..., description="retrieval | answer | chunking | edge_cases")
    score: float = Field(..., description="Overall category score 0-100")
    status: str = Field(..., description="pass | warn | fail")
    metrics: dict = Field(default_factory=dict, description="Category-specific metric breakdown")
    details: List[dict] = Field(default_factory=list, description="Per-item results")


class EvalReport(BaseModel):
    """Full evaluation report produced by run_eval.py."""

    version: str = Field(default="1.0")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp")
    categories: List[CategoryReport] = Field(..., description="Results per category")
    overall_score: float = Field(..., description="Weighted average across categories 0-100")
    overall_status: str = Field(..., description="pass | warn | fail")
