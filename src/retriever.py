import logging

from google.cloud import firestore
from google.oauth2 import service_account
from langchain_google_firestore import FirestoreVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class FirestoreRetriever:
    """Connects to Firestore and retrieves semantically similar document chunks."""

    def __init__(
        self,
        sa_path: str,
        project_id: str,
        location: str,
        collection: str,
        database: str,
        embedding_model: str,
        embedding_dimensions: int,
        logger: logging.Logger,
    ):
        self._sa_path = sa_path
        self._project_id = project_id
        self._location = location
        self._collection = collection
        self._database = database
        self._embedding_model = embedding_model
        self._embedding_dimensions = embedding_dimensions
        self._logger = logger
        self._vector_store: FirestoreVectorStore = None

    def setup(self) -> None:
        """Initialise the embeddings client and the Firestore vector store.

        Uses GoogleGenerativeAIEmbeddings with vertexai=True to match the
        exact configuration used by the indexing pipeline (Building-vector-db).
        """
        self._logger.info(
            "Setting up Gemini embeddings: %s (dim=%d)",
            self._embedding_model,
            self._embedding_dimensions,
        )

        credentials = service_account.Credentials.from_service_account_file(
            self._sa_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        embeddings = GoogleGenerativeAIEmbeddings(
            model=self._embedding_model,
            credentials=credentials,
            project=self._project_id,
            location=self._location,
            vertexai=True,
            output_dimensionality=self._embedding_dimensions,
        )

        self._logger.info(
            "Connecting to Firestore database '%s', collection '%s'",
            self._database,
            self._collection,
        )
        client = firestore.Client(project=self._project_id, database=self._database)
        self._vector_store = FirestoreVectorStore(
            collection=self._collection,
            embedding_service=embeddings,
            client=client,
        )
        self._logger.info("FirestoreRetriever setup complete.")

    def as_langchain_retriever(self, k: int = 4):
        """Expose the vector store as a LangChain BaseRetriever."""
        return self._vector_store.as_retriever(search_kwargs={"k": k})

