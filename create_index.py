"""
One-off script to create the required Firestore vector index.
Run once: .venv/Scripts/python.exe create_index.py
The index creation is async on GCP; it may take a few minutes to become active.
"""
from google.cloud.firestore_admin_v1 import FirestoreAdminClient
from google.cloud.firestore_admin_v1.types import Index, CreateIndexRequest
from src.settings import Settings

config = Settings()

admin_client = FirestoreAdminClient()

parent = (
    f"projects/{config.GCP_PROJECT_ID}/databases/{config.FIRESTORE_DATABASE}"
    f"/collectionGroups/{config.FIRESTORE_COLLECTION}"
)

index = Index(
    query_scope=Index.QueryScope.COLLECTION,
    fields=[
        Index.IndexField(
            field_path="embedding",
            vector_config=Index.IndexField.VectorConfig(
                dimension=768,
                flat=Index.IndexField.VectorConfig.FlatIndex(),
            ),
        )
    ],
)

print(f"Creating vector index on '{config.FIRESTORE_COLLECTION}' ...")
operation = admin_client.create_index(
    request=CreateIndexRequest(parent=parent, index=index)
)
print("Index creation started. Operation name:", operation.operation.name)
print("This may take a few minutes. Check progress at:")
print(f"  https://console.cloud.google.com/firestore/databases/{config.FIRESTORE_DATABASE}/indexes?project={config.GCP_PROJECT_ID}")
