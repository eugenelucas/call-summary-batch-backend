from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from typing import Optional
from core.email_send import send_email_feedback_link 
from fastapi import Form
from dbs.feedback_link import update_feedback, fetch_all_feedback, get_email_by_token

router = APIRouter()

@router.post("/send-email")
def send_email_endpoint(
    subject: str = Form(...),
    recipient: str = Form(...),
    surveylink: str = Form(...)
):
    send_email_feedback_link(subject, recipient, surveylink)
    return {"message": "Email sent successfully"}

@router.post("/submit-feedback")
def submit_feedback(token: str = Form(...), feedback: Optional[str] = Form(None), rate: str = Form(...)):
    success = update_feedback(token, feedback, rate)
    if not success:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    return {"message": "Feedback submitted successfully"}

@router.get("/all-feedback")
def get_all_feedback_endpoint():
    return {"feedbacks": fetch_all_feedback()}

@router.get("/token-to-email/{token}")
def token_to_email(token: str):
    email = get_email_by_token(token)
    if not email:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    return {"email": email}