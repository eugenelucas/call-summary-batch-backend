
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
import os

def get_secret_from_keyvault(secret_name: str) -> str:
    keyvault_url = f"https://{os.getenv('AZURE_KEYVAULT_NAME')}.vault.azure.net"

    credential = ClientSecretCredential(
        tenant_id=os.getenv("AZURE_KEYVAULT_TENANT_ID"),
        client_id=os.getenv("AZURE_KEYVAULT_CLIENT_ID"),
        client_secret=os.getenv("AZURE_KEYVAULT_CLIENT_SECRET"),
    )

    client = SecretClient(vault_url=keyvault_url, credential=credential)
    secret = client.get_secret(secret_name)
    return secret.value