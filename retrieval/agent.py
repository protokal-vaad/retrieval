import logging

from pydantic_ai import Agent

from retrieval.models import Document, RetrievalResult
from retrieval.request_guard import RequestGuard
from retrieval.retriever import FirestoreRetriever


RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer ONLY from the provided context. "
    "If the context does not contain the answer, say you don't have enough information.\n\n"
    "IMPORTANT INSTRUCTION FOR CITATION:\n"
    "At the very end of your answer, you MUST append a Hebrew citation block based on the sources you used.\n"
    "The citation MUST be in this exact format (replace the brackets with actual values):\n"
    "מידע זה נלקח מקובץ ‹שם הקובץ› עמודים/חלקים ‹...›\n"
    "You will be provided with [Source: ...] and [Section: ...] metadata for each context chunk. Use them to construct the citation."
)


class RAGAgent:
    """Pydantic AI RAG agent powered by Gemini 2.5 Flash."""

    def __init__(
        self,
        model_name: str,
        retriever: FirestoreRetriever,
        request_guard: RequestGuard,
        logger: logging.Logger,
        gcs_bucket_name: str = "",
    ):
        self._model_name = model_name
        self._retriever = retriever
        self._request_guard = request_guard
        self._logger = logger
        self._gcs_bucket_name = gcs_bucket_name
        self._agent: Agent = None

    def setup(self) -> None:
        """Initialise the Pydantic AI agent with the configured Gemini model."""
        self._logger.info("Initialising Pydantic AI agent with model: %s", self._model_name)
        self._agent = Agent(
            f"google-vertex:{self._model_name}",
            system_prompt=RAG_SYSTEM_PROMPT,
        )
        self._logger.info("RAGAgent setup complete.")

    def run(self, question: str) -> RetrievalResult:
        """Retrieve context from Firestore and generate an answer."""
        self._logger.info("Retrieving documents for: %s", question)
        raw_docs = self._retriever.retrieve(question, k=4)

        context_parts = []
        for i, doc in enumerate(raw_docs, 1):
            nested_metadata = doc.metadata.get("metadata", {})
            source = nested_metadata.get("source_file", "unknown")
            section = nested_metadata.get("section_type", "unknown")
            context_parts.append(f"--- Chunk {i} ---\n[Source: {source}]\n[Section: {section}]\n{doc.page_content}")

        context = "\n\n".join(context_parts)
        result = self._request_guard.run(
            f"answer generation for question: {question[:40]}",
            lambda: self._agent.run_sync(f"Context:\n{context}\n\nQuestion: {question}"),
        )

        source_documents = []
        for doc in raw_docs:
            nested = doc.metadata.get("metadata", {})
            flat_metadata = {
                "source_file": nested.get("source_file", "unknown"),
                "section_type": nested.get("section_type", "unknown"),
            }
            # Include other top-level metadata keys if any
            for k, v in doc.metadata.items():
                if k != "metadata":
                    flat_metadata[k] = v
            
            source_file = flat_metadata.get("source_file")
            if source_file and source_file != "unknown" and self._gcs_bucket_name:
                flat_metadata["gcs_url"] = f"https://storage.googleapis.com/{self._gcs_bucket_name}/{source_file}"
                
            source_documents.append(Document(content=doc.page_content, metadata=flat_metadata))

        self._logger.info("Answer generated. Sources: %d", len(source_documents))
        return RetrievalResult(
            question=question,
            answer=result.output,
            source_documents=source_documents,
        )
