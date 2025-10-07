from fastapi import APIRouter
from typing import List


router = APIRouter()

@router.get("/models", response_model=List[str])
def list_models():
    return ["AzureOpenAI", "ChatGroq"]