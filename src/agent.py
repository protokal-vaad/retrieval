import logging

from pydantic_ai import Agent

from src.models import Document, RetrievalResult
from src.retriever import FirestoreRetriever


RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer ONLY from the provided context. "
    "If the context does not contain the answer, say you don't have enough information."
)


class RAGAgent:
    """Pydantic AI RAG agent powered by Gemini 2.5 Flash."""

    def __init__(
        self,
        model_name: str,
        retriever: FirestoreRetriever,
        logger: logging.Logger,
    ):
        self._model_name = model_name
        self._retriever = retriever
        self._logger = logger
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
        raw_docs = self._retriever.as_langchain_retriever(k=4).invoke(question)

        context = "\n\n".join(doc.page_content for doc in raw_docs)
        result = self._agent.run_sync(f"Context:\n{context}\n\nQuestion: {question}")

        source_documents = [
            Document(content=doc.page_content, metadata=doc.metadata)
            for doc in raw_docs
        ]

        self._logger.info("Answer generated. Sources: %d", len(source_documents))
        return RetrievalResult(
            question=question,
            answer=result.output,
            source_documents=source_documents,
        )
