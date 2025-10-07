from core.keyvault import get_secret_from_keyvault
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import smtplib
from dbs.feedback_link import save_token_email

def send_email_feedback_link(subject: str, recipient: str, surveylink: str):

    token = str(uuid.uuid4())
    save_token_email(recipient, token)
    survey_link = f"{surveylink}?token={token}"

    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = get_secret_from_keyvault("EMAILPASSWORD")
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject
    body = f'''
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Hello,</p>
                <p>Thank you for taking the time to speak with our support team today.  
                We value your opinion and would greatly appreciate it if you could take a moment to share your feedback.</p>
                
                <p>
                <a href="{survey_link}"
                    style="background-color: #0078d4; color: #fff; padding: 10px 20px; 
                            text-decoration: none; border-radius: 5px; display: inline-block;">
                    Take the Survey
                </a>
                </p>
                
                <p>Your quick response will help us improve our services and better serve you in the future.  
                Thank you again for your time and feedback.</p>
                
                <p>Thank you</p>
            </body>
            </html>'''
    msg.attach(MIMEText(body, "html"))
    try:
        server = smtplib.SMTP("smtp.office365.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
    except Exception as e:
        print("Failed to send email:", e)


def send_email(subject: str, recipient: str, body: str):
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = get_secret_from_keyvault("EMAILPASSWORD")
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.office365.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
    except Exception as e:
        print("Failed to send email:", e)                                                       