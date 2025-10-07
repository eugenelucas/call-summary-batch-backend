from fastapi import APIRouter,WebSocket,HTTPException
from core.anomaly_detection import anomaly_detection_sementic
from dbs.audio import get_audio_files
from core.report import transcribe_audio_openai
import json
from typing import List, Dict,Optional,Any
from dbs.db_connections import get_db_connection
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

@router.post("/anomaly-details")
async def get_audio_anomalies(filename:str): 
    """
    Returns the audio file name and its anomaly reasons.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            s.AudioFileName,
            r.value AS anomaly_reason
        FROM Statistic s
        OUTER APPLY OPENJSON(s.AnomalyReason) r
        WHERE s.AudioFileName = ?
    """

    cursor.execute(query, (filename,))
    rows = cursor.fetchall()

    # Aggregate anomaly reasons
    anomaly_reasons = [row.anomaly_reason for row in rows if row.anomaly_reason]

    return {
        "audio_filename": rows[0].AudioFileName if rows else filename,
        "anomaly_reasons": anomaly_reasons
    }

@router.post("/anomaly-agent-details")
async def get_audio_anomalies_from_agent(agentname:str): 
    """
    Returns the audio file name and its anomaly reasons.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            ag.name AS agent_name,
            af.filename AS audio_filename,
            aa.AnomalyReason AS anomaly_reasons
        FROM audio_files af
        JOIN Agents ag ON af.agent_id = ag.id
        JOIN [dbo].[Statistic] aa ON af.filename = aa.AudioFileName
        WHERE aa.Anomaly = 'True' AND ag.name = ? ;

"""

    cursor.execute(query, (agentname,))
    rows = cursor.fetchall()

    result = []
    for row in rows: 
        try:
            reasons = json.loads(row.anomaly_reasons)
        except Exception:
            reasons = [row.anomaly_reasons]  # fallback if not JSON

        result.append({ 
            "audio_filename": row.audio_filename,
            "anomaly_reasons": reasons
        })

    cursor.close()
    conn.close()

    return result 