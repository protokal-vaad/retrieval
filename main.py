import os
from src.settings import Settings
from src.logger import AppLogger
from src.retriever import FirestoreRetriever
from src.agent import RAGAgent
from src.app import GradioApp


def main():
    # Load all configuration from .env
    config = Settings()

    # Set GCP credentials environment variable for SDK clients
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS
    os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

    # Initialise logger
    logger = AppLogger(level=config.LOG_LEVEL).get()
    logger.info("Starting RAG Retrieval System.")

    # Build and initialise the Firestore retriever (Dependency Injection)
    retriever = FirestoreRetriever(
        project_id=config.GCP_PROJECT_ID,
        location=config.VERTEXAI_LOCATION,
        collection=config.FIRESTORE_COLLECTION,
        database=config.FIRESTORE_DATABASE,
        embedding_model=config.EMBEDDING_MODEL,
        logger=logger,
    )
    retriever.setup()

    # Build and initialise the RAG agent
    agent = RAGAgent(
        model_name=config.MODEL_NAME,
        project_id=config.GCP_PROJECT_ID,
        location=config.VERTEXAI_LOCATION,
        retriever=retriever,
        logger=logger,
    )
    agent.setup()

    # Build and launch the Gradio UI
    app = GradioApp(agent=agent, logger=logger)
    app.setup()
    app.launch()


if __name__ == "__main__":
    main()
