from fastapi import APIRouter
from fastapi import HTTPException 
from typing import Optional 
from fastapi import Form 
import os
from core.servicenow import get_servicenow_access_token, get_incident_sys_id
from core.servicenow import ServiceNowPDFUploader
router = APIRouter()

@router.post("/submit-feedback-servicenow")
def submit_feedback_servicenow_endpoint(
    incident_number: str = Form(...), feedback: Optional[str] = Form(None), rate: str = Form(...)
):

    servicenow_instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
    servicenow_access_token = get_servicenow_access_token()

    if not servicenow_instance_url or not servicenow_access_token: 
        return {"success": False, "incident_number": incident_number, "result": "Missing ServiceNow configuration"}

    try:
        # Check if incident exists
        sys_id = get_incident_sys_id(servicenow_instance_url, servicenow_access_token, incident_number)
        if not sys_id: 
            return {"success": False, "incident_number": incident_number, "result": "Incident {incident_number} not found"}

       

        # Upload PDF to ServiceNow incident
        uploader = ServiceNowPDFUploader(servicenow_instance_url, servicenow_access_token)
        upload_result = uploader.upload_feedback_file(sys_id,feedback,rate)

        return {"success": True, "incident_number": incident_number, "result": upload_result}

    except Exception as e: 
        return {"success": False, "incident_number": incident_number, "result": f"Upload failed: {str(e)}"}