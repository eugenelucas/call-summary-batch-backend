from azure.storage.blob import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

import os
from datetime import datetime
from fastapi import  UploadFile

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")  


def upload_pdf_to_blob(buffer, filename: str, prefix: str = "fallback") -> str:
    """
    Uploads PDF buffer to Azure Blob Storage and returns blob URL.
    """
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        
    try:
        container_client.create_container()
    except Exception:
        pass  # Already exists

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    blob_name = f"{prefix}/{timestamp}_{filename}"

    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(buffer.getvalue(), overwrite=True)
    return blob_client.url


def upload_audio_to_blob(file: UploadFile) -> str:
    """
    Uploads audio file to Azure Blob Storage and returns blob URL.
    """
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        
    try:
        container_client.create_container()
    except Exception:
        pass  # Already exists
 
    blob_name = f"{file.filename}"

    blob_client = container_client.get_blob_client(blob_name)
    # Upload directly from file object stream
    blob_client.upload_blob(file.file, overwrite=True)
    return blob_client.url

def generate_audio_sas_url(blob_name: str):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    account_name = blob_service_client.account_name
    key = blob_service_client.credential.account_key

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=AZURE_STORAGE_CONTAINER_NAME,
        blob_name=blob_name,
        account_key=key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=15)
    )

    url = f"https://{account_name}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER_NAME}/{blob_name}?{sas_token}"
    return url