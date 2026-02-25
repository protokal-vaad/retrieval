import logging

from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_vertexai import ChatVertexAI

from src.models import Document, RetrievalResult
from src.retriever import FirestoreRetriever


# RAG prompt that instructs the model to answer only from provided context
RAG_PROMPT_TEMPLATE = """You are a helpful assistant. Use ONLY the following context to answer the question.
If the context does not contain the answer, say that you don't have enough information.

Context:
{context}

Question: {question}

Answer:"""


def _format_docs(docs) -> str:
    """Concatenate document page contents into a single context string."""
    return "\n\n".join(doc.page_content for doc in docs)


class RAGAgent:
    """LangChain LCEL RAG agent powered by Gemini on Vertex AI."""

    def __init__(
        self,
        model_name: str,
        project_id: str,
        location: str,
        retriever: FirestoreRetriever,
        logger: logging.Logger,
    ):
        self._model_name = model_name
        self._project_id = project_id
        self._location = location
        self._retriever = retriever
        self._logger = logger
        self._chain = None  # RunnableParallel chain built in setup()

    def setup(self) -> None:
        """Build the LCEL chain: retriever → prompt → LLM → parser."""
        self._logger.info("Initialising ChatVertexAI with model: %s", self._model_name)
        llm = ChatVertexAI(
            model_name=self._model_name,
            project=self._project_id,
            location=self._location,
            temperature=0,
        )

        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=RAG_PROMPT_TEMPLATE,
        )

        lc_retriever = self._retriever.as_langchain_retriever(k=4)

        # Sub-chain: receives {"context": [docs], "question": str} → answer str
        answer_chain = (
            RunnablePassthrough.assign(context=lambda x: _format_docs(x["context"]))
            | prompt
            | llm
            | StrOutputParser()
        )

        # Parallel chain: retriever and passthrough run together, then answer is assigned.
        # Single retriever call returns both raw docs and the generated answer.
        self._chain = RunnableParallel(
            context=lc_retriever,
            question=RunnablePassthrough(),
        ).assign(answer=answer_chain)

        self._logger.info("RAGAgent setup complete (LCEL).")

    def run(self, question: str) -> RetrievalResult:
        """Execute the RAG pipeline for a user question and return a RetrievalResult."""
        self._logger.info("Running RAG agent for question: %s", question)

        # Single invocation: retriever runs once, answer generated in parallel
        result = self._chain.invoke(question)

        answer = result["answer"]
        raw_docs = result["context"]

        source_documents = [
            Document(content=doc.page_content, metadata=doc.metadata)
            for doc in raw_docs
        ]

        self._logger.info("Answer generated. Source documents: %d", len(source_documents))
        return RetrievalResult(
            question=question,
            answer=answer,
            source_documents=source_documents,
        )
