import os
import sys
from src.settings import Settings
from src.logger import AppLogger
from src.retriever import FirestoreRetriever
from src.agent import RAGAgent


TEST_QUESTION = "מה הנושאים שנלמדים בקורס?"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    config = Settings()

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

    logger = AppLogger(level=config.LOG_LEVEL).get()
    logger.info("Testing vector DB connection with one question.")

    retriever = FirestoreRetriever(
        project_id=config.GCP_PROJECT_ID,
        location=config.VERTEXAI_LOCATION,
        collection=config.FIRESTORE_COLLECTION,
        database=config.FIRESTORE_DATABASE,
        embedding_model=config.EMBEDDING_MODEL,
        logger=logger,
    )
    retriever.setup()

    agent = RAGAgent(
        model_name=config.MODEL_NAME,
        retriever=retriever,
        logger=logger,
    )
    agent.setup()

    result = agent.run(TEST_QUESTION)

    print(f"\n{'=' * 60}")
    print(f"Question : {result.question}")
    print(f"\nAnswer   :\n{result.answer}")
    print(f"\nSources  : {len(result.source_documents)} document(s)")
    for i, doc in enumerate(result.source_documents, 1):
        print(f"  [{i}] {doc.content[:120]}...")
    print("=" * 60)


if __name__ == "__main__":
    main()
