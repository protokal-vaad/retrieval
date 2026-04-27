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
