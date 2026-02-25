import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """All application settings loaded from the .env file."""

    # Google Cloud
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(..., description="Path to the GCP service account JSON")
    GCP_PROJECT_ID: str = Field(..., description="GCP project ID")

    # Locations — split because Gemini runs in us-central1 but Firestore DB is in me-west1
    VERTEXAI_LOCATION: str = Field(..., description="Vertex AI region for Gemini and embedding models")
    FIRESTORE_LOCATION: str = Field(..., description="Region where the Firestore database lives")

    # Firestore
    FIRESTORE_DATABASE: str = Field(..., description="Firestore database ID")
    FIRESTORE_COLLECTION: str = Field(..., description="Firestore collection storing vector embeddings")

    # Models
    MODEL_NAME: str = Field(..., description="Vertex AI chat model name")
    EMBEDDING_MODEL: str = Field(..., description="Vertex AI embedding model name")

    # API Key
    GOOGLE_API_KEY: str = Field(..., description="Google Gemini API key")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
