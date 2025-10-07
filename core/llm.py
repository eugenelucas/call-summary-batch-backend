from langchain_openai import AzureChatOpenAI
import os

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = "2024-02-01"

client = AzureChatOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)
