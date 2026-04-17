from pydantic import BaseModel, Field
from typing import List


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
    question: str = Field(..., description="Hebrew question posed to the RAG system")
    answer: str = Field(..., description="RAG system answer — baseline for regression")
    num_sources: int = Field(..., description="Number of retrieved source documents")
    source_previews: List[str] = Field(default_factory=list, description="First 120 chars of each source")


class EvalSet(BaseModel):
    """Complete evaluation set saved to eval_set.json."""

    version: str = Field(default="1.0", description="Schema version")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp of build time")
    total_items: int = Field(..., description="Total Q&A pairs")
    items: List[EvalItem] = Field(..., description="Ordered evaluation items")
