from fastapi import APIRouter
from typing import List, Dict,Optional
from dbs.statistics import get_agent_statistics
from fastapi import   Query 
from datetime import datetime

router = APIRouter()

@router.get("/agent_statistics", response_model=List[Dict])
def agent_statistics(
    start_datetime: Optional[datetime] = Query(None, description="Start datetime (YYYY-MM-DD HH:MM:SS)"),
    end_datetime: Optional[datetime] = Query(None, description="End datetime (YYYY-MM-DD HH:MM:SS)")

):
    """
    Endpoint to get statistics for all agents.
    """
    return get_agent_statistics(start_datetime, end_datetime)