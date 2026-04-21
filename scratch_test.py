import sys, os
from src.settings import Settings
from src.logger import AppLogger
from src.retriever import FirestoreRetriever
from src.eval_retrieval import RetrievalEvaluator
from src.models import EvalItem
from build_eval import _QUESTIONS

config = Settings()
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config.GOOGLE_APPLICATION_CREDENTIALS
logger = AppLogger(level=config.LOG_LEVEL).get()

retriever = FirestoreRetriever(
    sa_path=config.GOOGLE_APPLICATION_CREDENTIALS,
    project_id=config.GCP_PROJECT_ID,
    location=config.VERTEXAI_LOCATION,
    collection=config.FIRESTORE_COLLECTION,
    database=config.FIRESTORE_DATABASE,
    embedding_model=config.EMBEDDING_MODEL,
    embedding_dimensions=config.EMBEDDING_DIMENSIONS,
    logger=logger,
)
retriever.setup()

items = []
for i, q in enumerate(_QUESTIONS, start=1):
    if q["category"] in ("broad", "cross_protocol"):
        item = EvalItem(
            id=i,
            round=q["round"],
            category=q["category"],
            question=q["question"],
            answer="MOCKED ANSWER",
            num_sources=0,
            expected_source_files=q.get("expected_source_files", []),
            expected_section_types=q.get("expected_section_types", [])
        )
        items.append(item)

retrieval_eval = RetrievalEvaluator(retriever=retriever, logger=logger)
report = retrieval_eval.evaluate_all(items)
print(f'Score: {report.score} | Status: {report.status}')
print(report.metrics)

# print details
for detail in report.details:
    print(f"Q{detail['question_id']} Hit: {detail['hit']} RR: {detail['reciprocal_rank']} Prec: {detail['precision']}")
