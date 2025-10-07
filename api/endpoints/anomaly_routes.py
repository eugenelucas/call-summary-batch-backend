from fastapi import APIRouter,WebSocket,HTTPException
from core.anomaly_detection import anomaly_detection_sementic
from dbs.audio import get_audio_files
from core.report import transcribe_audio_openai
import json
router = APIRouter()

@router.post("/anomaly-detection-text")
async def anomaly_detection_text(raw_text:str):
    if not raw_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    resp = await anomaly_detection_sementic(raw_text)
    return resp

@router.post("/anomaly-detection-audio")
async def anomaly_detection_audio_file(filename:str):
    files = get_audio_files()
    audio_path = files[filename]
    result = transcribe_audio_openai(audio_path)
    transcribe_text = result["text"] 
    resp = await anomaly_detection_sementic(transcribe_text)
    return resp
    