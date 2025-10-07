from fastapi import APIRouter,WebSocket,HTTPException
import os
import asyncio
import azure.cognitiveservices.speech as speechsdk
from starlette.websockets import WebSocketState
from core.transcribe import auto_correct_text
import json
from core.anomaly_detection import anomaly_detection_sementic
router = APIRouter()

SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT")

@router.websocket("/ws/transcribe")
async def websocket_transcribe(ws: WebSocket):
    await ws.accept()
    config_msg = await ws.receive_json()
    enable_auto_correct = config_msg.get("auto_correct", True)
    enable_anomaly = config_msg.get("anomaly", True)
    
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, endpoint=SPEECH_ENDPOINT)
    speech_config.speech_recognition_language = "en-US"
    speech_config.set_property(
        property_id=speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults,
        value="true"
    )

    format = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
    stream = speechsdk.audio.PushAudioInputStream(stream_format=format)
    audio_config = speechsdk.audio.AudioConfig(stream=stream)
    transcriber = speechsdk.transcription.ConversationTranscriber(
        speech_config=speech_config, audio_config=audio_config
    )

    loop = asyncio.get_event_loop()
    stop_future = loop.create_future()

    # INTERMEDIATE results
    def transcribing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        if evt.result.text:
            asyncio.run_coroutine_threadsafe(
                ws.send_json({
                    "type": "transcribing", 
                    "text": evt.result.text
                }),
                loop
            )

    # FINAL results
    def transcribed_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text = evt.result.text
            asyncio.run_coroutine_threadsafe(
                ws.send_json({
                    "type": "transcribed", 
                    "text": text
                }),
                loop
            )
            if enable_auto_correct or enable_anomaly:
                asyncio.run_coroutine_threadsafe(
                    handle_backend_processing(ws, text, enable_auto_correct, enable_anomaly),
                    loop
                )

    def stop_cb(evt):
        if not stop_future.done():
            stop_future.set_result(True)

    transcriber.transcribing.connect(transcribing_cb)
    transcriber.transcribed.connect(transcribed_cb)
    transcriber.canceled.connect(stop_cb)
    transcriber.session_stopped.connect(stop_cb)

    transcriber.start_transcribing_async()

    try:
        while True:
            data = await ws.receive_bytes()
            stream.write(data)
    except Exception:
        pass
    finally:
        stream.close()
        await stop_future
        transcriber.stop_transcribing_async()
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.close()

@router.get("/ws/transcribe")
def ws_transcribe_doc():
    """
    ⚠️ WebSocket Endpoint

    **URL:** ws/transcribe  
    **Method:** WebSocket  

    **Description:**  
    - Send: raw 16-bit PCM audio bytes  
    - Receive JSON messages:  
        - `{"type": "transcribing", "text": "..."}`  
        - `{"type": "transcribed", "text": "..."}`  
    """
    return {"message": "This endpoint is only for documentation; use WebSocket at /ws/transcribe."}

@router.post("/auto-correct", )
async def auto_correct_endpoint(raw_text:str):
    if not raw_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    corrected = await auto_correct_text(raw_text)
    return {"corrected_text": corrected}

async def handle_backend_processing(ws: WebSocket, text: str, auto_correct: bool, anomaly: bool):
    if auto_correct:
        corrected = await auto_correct_text(text)
        await ws.send_text(json.dumps({"type": "auto_corrected", "text": corrected}))

    if anomaly:
        anomaly_result = await anomaly_detection_sementic(text)
        await ws.send_text(json.dumps({"type": "anomaly", **anomaly_result}))