from typing import TypedDict, Optional,List,Dict,Any
from pydantic import BaseModel,Field

# In your response model
class CallOutItem(BaseModel):
    time_sec: int
    label: str
    description: str
    
# Request/Response models

class ProcessRequest(BaseModel):
    filenames: List[str] # ✅ changed: support multiple files
    model_option: str

class AnomalyDetectionResult(BaseModel):
    isAnomaly: bool
    anomalyCount: int
    reasons: List[str]

class FileProcessResponse(BaseModel):
    call_summary: str
    sentiment: str
    sentiment_score: int
    call_purpose: str
    speaker_insights: Dict[str, str]
    email_sent: List[str]
    action_items: Optional[List[Dict[str, str]]] = None
    Agent_rating: int
    Customer_name: str
    Agent_name: str
    sentiment_chunks: Optional[list] = None
    call_outs: List[CallOutItem] = Field(default_factory=list) # New response field
    anomaly_detection: AnomalyDetectionResult 
    inc_number: Optional[str] = None 

class BatchProcessResponse(BaseModel):
    results: Dict[str, FileProcessResponse] # ✅ per filename


class State(TypedDict):
    audio_path: str
    transcription: Optional[str]
    call_summary: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[int]
    call_purpose: Optional[str]
    speaker_insights: Optional[Any]
    Agent_rating: Optional[int]
    Customer_name: Optional[str]
    Agent_name: Optional[str]
    action_items: Optional[Any]
    sentiment_chunks: Optional[List[dict]]
    call_outs: Optional[List[dict]]
    audio_duration:int
