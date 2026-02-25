import logging

from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_firestore import FirestoreVectorStore


class FirestoreRetriever:
    """Connects to Firestore and retrieves semantically similar document chunks."""

    def __init__(
        self,
        project_id: str,
        location: str,
        collection: str,
        database: str,
        embedding_model: str,
        logger: logging.Logger,
    ):
        self._project_id = project_id
        self._location = location
        self._collection = collection
        self._database = database
        self._embedding_model = embedding_model
        self._logger = logger
        self._vector_store: FirestoreVectorStore = None

    def setup(self) -> None:
        """Initialise the VertexAI embeddings and the Firestore vector store."""
        self._logger.info("Setting up VertexAI embeddings: %s", self._embedding_model)
        embeddings = VertexAIEmbeddings(
            model_name=self._embedding_model,
            project=self._project_id,
            location=self._location,
        )

        self._logger.info(
            "Connecting to Firestore database '%s', collection '%s'",
            self._database,
            self._collection,
        )
        self._vector_store = FirestoreVectorStore(
            collection=self._collection,
            embedding_service=embeddings,
            client=self._build_firestore_client(),
        )
        self._logger.info("FirestoreRetriever setup complete.")

    def _build_firestore_client(self):
        """Build an authenticated Firestore client for the configured database."""
        from google.cloud import firestore

        return firestore.Client(
            project=self._project_id,
            database=self._database,
        )

    def as_langchain_retriever(self, k: int = 4):
        """Expose the vector store as a LangChain BaseRetriever."""
        return self._vector_store.as_retriever(search_kwargs={"k": k})

