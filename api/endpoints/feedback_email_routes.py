from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from typing import Optional
from core.email_send import send_email_feedback_link 
from fastapi import Form
from dbs.feedback_email import upsert_feedback_email, fetch_all_feedback_email

router = APIRouter()


@router.post("/submit-feedback-email")
def submit_feedback(email: str = Form(...),  feedback: Optional[str] = Form(None), rate: str = Form(...)):
    success = upsert_feedback_email(email, feedback, rate)
    if not success:
        raise HTTPException(status_code=404, detail="Failed")
    return {"message": "Feedback submitted successfully"}

@router.get("/all-feedback-email")
def get_all_feedback_endpoint():
    return {"feedbacks": fetch_all_feedback_email()}
