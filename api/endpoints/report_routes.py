from fastapi import APIRouter, Query,Request,HTTPException,UploadFile, File, Form
from core.servicenow import get_servicenow_access_token, get_incident_sys_id
from dbs.audio import get_audio_files
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
import plotly.graph_objs as go
from core.report import extract_inc_number, generate_pdf_report
from core.blob import upload_pdf_to_blob
from core.servicenow import ServiceNowPDFUploader
from typing import Dict, List
import os
import tempfile
from core.models import BatchProcessResponse, ProcessRequest,CallOutItem,FileProcessResponse
from core.report import process_email_notifications, create_pipeline, load_llm
from core.anomaly_detection import anomaly_detection_sementic
from dbs.statistics import insert_statistics

router = APIRouter()

processed_calls: Dict[str, List[dict]] = {}


@router.get("/check-incidient-number-from-audio")
def check_incident_number(filename: str = Query(..., description="The filename of the processed audio file")):
    if not filename or filename not in processed_calls:
        raise HTTPException(status_code=404, detail="No processed call available. Run /process-call first.")

    files = get_audio_files()
    audio_path = files[filename]
    state = processed_calls[filename]
    inc_number = extract_inc_number(state)
    servicenow_instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
    servicenow_access_token = get_servicenow_access_token()
    if not inc_number:
        return {"incident_number": None, "valid": None}
    else:
        sys_id = get_incident_sys_id(servicenow_instance_url, servicenow_access_token, inc_number)
        if not sys_id:
            return {"incident_number": inc_number, "valid": False}
        else:
            return {"incident_number": inc_number, "valid": True}
    

@router.get("/check-incidient-number")
def check_incident_number(inc_number: str = Query(..., description="The filename of the processed audio file")):
    servicenow_instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
    servicenow_access_token = get_servicenow_access_token()
    sys_id = get_incident_sys_id(servicenow_instance_url, servicenow_access_token, inc_number)

    if not sys_id:
        return {"incident_number": inc_number, "valid": False}
    else:
        return {"incident_number": inc_number, "valid": True}
    



@router.get("/download-report")
def download_report(filename: str = Query(..., description="The filename of the processed audio file"),
                    incident_number: str = Query(None, description="Optional incident number. If not provided, it will be extracted.")
                    ):

    if not filename or filename not in processed_calls:
        raise HTTPException(status_code=404, detail="No processed call available. Run /process-call first.")

    files = get_audio_files()
    audio_path = files[filename]
    state = processed_calls[filename]
    if incident_number:
        inc_number = incident_number
    else:
        inc_number = extract_inc_number(state)
        
    pdf_buffer = generate_pdf_report(filename,state)
    
    if not inc_number:
        print("No INC found, uploading to Azure Blob Storage...")
        blob_url = upload_pdf_to_blob(pdf_buffer, f"Call_Summary_{filename}.pdf", prefix="no-inc")
        upload_result = {"uploaded_to": "azure_blob", "blob_url": blob_url}
    else:
        
        servicenow_instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
        servicenow_access_token = get_servicenow_access_token()
        upload_result = None

        if servicenow_instance_url and servicenow_access_token:
            try:
                uploader = ServiceNowPDFUploader(servicenow_instance_url, servicenow_access_token)
 
                sys_id = get_incident_sys_id(servicenow_instance_url, servicenow_access_token, inc_number)
                if not sys_id:
                        print(f"Incident {inc_number} not found. Uploading to Azure Blob Storage...")
                        blob_url = upload_pdf_to_blob(pdf_buffer, f"Call_Summary_{filename}.pdf", prefix="incident-not-found")
                        upload_result = {"uploaded_to": "azure_blob", "blob_url": blob_url}

                else:
                    # Upload to ServiceNow
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                        tmp_pdf.write(pdf_buffer.getvalue())
                        tmp_pdf_path = tmp_pdf.name
                    upload_result = uploader.upload_pdf_to_incident(
                        sys_id,
                        tmp_pdf_path,
                        custom_filename=f"Call_Summary_{filename}.pdf"
                    )
                    os.remove(tmp_pdf_path)

            except Exception as e:
                upload_result = {"error": str(e)}
        else:
            print("Missing ServiceNow config. Uploading to Azure Blob Storage...")
            blob_url = upload_pdf_to_blob(pdf_buffer, f"Call_Summary_{filename}.pdf", prefix="no-servicenow")
            upload_result = {"uploaded_to": "azure_blob", "blob_url": blob_url}

    response = StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Call_Summary_{filename}.pdf",
            "X-ServiceNow-Upload-Result": str(upload_result)[:2000]  # Truncate for header safety
        }
    )
    return response

@router.post("/upload-report-to-incident")
async def upload_report_to_incident(
    incident_number: str = Form(..., description="ServiceNow incident number"),
    file: UploadFile = File(..., description="PDF report file")
):
    # Check ServiceNow configuration
    servicenow_instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
    servicenow_access_token = get_servicenow_access_token()

    if not servicenow_instance_url or not servicenow_access_token: 
        return {"success": False, "incident_number": incident_number, "result": "Missing ServiceNow configuration"}

    try:
        # Check if incident exists
        sys_id = get_incident_sys_id(servicenow_instance_url, servicenow_access_token, incident_number)
        if not sys_id: 
            return {"success": False, "incident_number": incident_number, "result": "Incident {incident_number} not found"}

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            contents = await file.read()
            tmp_pdf.write(contents)
            tmp_pdf_path = tmp_pdf.name

        # Upload PDF to ServiceNow incident
        uploader = ServiceNowPDFUploader(servicenow_instance_url, servicenow_access_token)
        upload_result = uploader.upload_pdf_to_incident(
            sys_id,
            tmp_pdf_path,
            custom_filename = f"Incident_{incident_number}_{file.filename or 'report.pdf'}"
        )

        # Cleanup
        os.remove(tmp_pdf_path)

        return {"success": True, "incident_number": incident_number, "result": upload_result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/sentiment-graph-interactive")
def sentiment_graph_interactive(filename: str = Query(..., description="The filename of the processed audio file")):
    if not filename or filename not in processed_calls:
        raise HTTPException(status_code=404, detail="No processed call available. Run /process-call first.")
    state = processed_calls[filename]
    chunks = state.get("sentiment_chunks", [])
    if not chunks:
        raise HTTPException(status_code=204, detail="No sentiment chunks available")

    mapping = {"negative": -1, "neutral": 0, "positive": 1}
    reverse_map = {-1: "Negative", 0: "Neutral", 1: "Positive"}
    times = [c["time_sec"] for c in chunks]
    values = [mapping.get(c["sentiment"], 0) for c in chunks]
    labels = [c["sentiment"].capitalize() for c in chunks]

    trace = go.Scatter(
        x=times,
        y=values,
        mode="lines+markers",
        text=labels,  # hover text
        hoverinfo="text+x",  # display time and sentiment
        line=dict(shape='hv', width=2)
    )

    layout = go.Layout(
        title="Interactive Sentiment Timeline",
        xaxis=dict(title="Time (s)"),
        yaxis=dict(title="Sentiment", tickvals=[-1, 0, 1], ticktext=["Negative", "Neutral", "Positive"]),
        hovermode="x unified"
    )

    fig = go.Figure(data=[trace], layout=layout)
    return JSONResponse(content=fig.to_dict())


@router.post("/process-calls", response_model=BatchProcessResponse)
async def process_calls(req: ProcessRequest, request: Request):
    files = get_audio_files()
    results = {}


    for filename in req.filenames:
        if filename not in files:
            raise HTTPException(status_code=404, detail=f"Audio file not found: {filename}")


        audio_path = files[filename]
        try:
            llm = load_llm(req.model_option)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


        pipeline = create_pipeline(llm)
        state = pipeline.invoke({"audio_path": audio_path})


        # Convert call_outs to proper Pydantic models
        call_out_items = [
            CallOutItem(
                time_sec=item["time_sec"],
                label=item["label"],
                description=item["description"]
            )
            for item in state.get("call_outs", [])
        ]


        processed_calls[filename] = state
        incident_number = extract_inc_number(state)
        emails = process_email_notifications(state)

        #Anomal Detection
        transcribed_text = state.get("transcription", "")
        anomaly_result = await anomaly_detection_sementic(transcribed_text)

        #statics
        insert_statistics(
            filename,
            state.get("audio_duration"),
            state.get("Agent_rating"),
            state.get("sentiment_score"),
            anomaly_result.get("isAnomaly"),
            anomaly_result.get("reasons")
        )
        results[filename] = FileProcessResponse(
            call_summary=state["call_summary"],
            sentiment=state["sentiment"],
            sentiment_score=state["sentiment_score"],
            call_purpose=state["call_purpose"],
            speaker_insights=state.get("speaker_insights"),
            Agent_rating=state.get("Agent_rating"),
            action_items=state.get("action_items"),
            email_sent=emails,
            sentiment_chunks=state.get("sentiment_chunks"),
            Customer_name=state.get("Customer_name"),
            Agent_name=state.get("Agent_name"),
            call_outs=call_out_items,
            anomaly_detection=anomaly_result,
            inc_number=incident_number
        )


    return BatchProcessResponse(results=results)