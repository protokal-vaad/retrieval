import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from retrieval.settings import Settings
from retrieval.logger import AppLogger
from retrieval.request_guard import RequestGuard
from retrieval.retriever import FirestoreRetriever
from retrieval.agent import RAGAgent
from retrieval.models import RetrievalResult

class AskRequest(BaseModel):
    question: str

# Global references for dependency injection
agent: RAGAgent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    config = Settings()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

    app_logger = AppLogger(level=config.LOG_LEVEL)
    app_logger.setup()
    logger = app_logger.get()
    
    logger.info("Starting FastAPI service setup")

    request_guard = RequestGuard(logger=logger)
    request_guard.setup()

    retriever = FirestoreRetriever(
        sa_path=config.GOOGLE_APPLICATION_CREDENTIALS,
        project_id=config.GCP_PROJECT_ID,
        location=config.VERTEXAI_LOCATION,
        collection=config.FIRESTORE_COLLECTION,
        database=config.FIRESTORE_DATABASE,
        embedding_model=config.EMBEDDING_MODEL,
        embedding_dimensions=config.EMBEDDING_DIMENSIONS,
        request_guard=request_guard,
        logger=logger,
    )
    retriever.setup()

    agent = RAGAgent(
        model_name=config.MODEL_NAME,
        retriever=retriever,
        request_guard=request_guard,
        logger=logger,
        gcs_bucket_name=config.GCS_BUCKET_NAME,
    )
    agent.setup()
    
    yield
    
    logger.info("Shutting down FastAPI service")


app = FastAPI(lifespan=lifespan, title="Protokal Retrieval API")

@app.get("/health")
def health():
    return {"status": "ok", "agent_loaded": agent is not None}

@app.post("/ask", response_model=RetrievalResult)
def ask(request: AskRequest):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")
    try:
        return agent.run(request.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

_PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
app.mount("/", StaticFiles(directory=_PUBLIC_DIR, html=True), name="public")
