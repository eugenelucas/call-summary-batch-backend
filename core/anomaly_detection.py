 
from openai import AzureOpenAI
import json
import os
from pydantic import BaseModel
from dotenv import load_dotenv

class AnomalyEvent(BaseModel):
    isAnomaly: bool
    anomalyCount: int
    reasons: list[str]
 

async def anomaly_detection_sementic(text: str) -> dict:
    """
    Call Azure OpenAI for anomaly detection in transcripts.
    Returns JSON with anomaly flag, count, and reasons.
    """
    
    client = AzureOpenAI(
        azure_endpoint =  os.getenv("AZURE_OPENAI_ENDPOINT") ,
        api_key=os.getenv("AZURE_OPENAI_KEY"),  
        api_version="2025-01-01-preview"
        )
    
    system_prompt = """
    You are a strict JSON classifier. Given a call transcript, decide if it indicates one or more anomalies (possible fraud).
    "Anomaly" includes:
      - Requests for or attempts to reveal sensitive personal data (PII): SSN, social security number, credit/debit card numbers, CVV, PIN, passwords, bank account/routing numbers, driver's license, passport, national ID, mother's maiden name, security questions, OTP/2FA codes, etc.
      - Repeated or suspicious attempts to obtain account/benefit/claim details.
      - Contradictory or inconsistent statements about identity, account, or intent.
      - Scripted scam-like patterns (IRS scam, IT support scam, insurance fraud, etc.).
      - Mismatch between caller-provided information and metadata/context (e.g., location).
      - Emotional manipulation, urgency, or pressure tactics to bypass normal flow.

    Return ONLY a compact JSON object in this format:
    {{
      "isAnomaly": <true|false>,
      "anomalyCount": <number>,
      "reasons": ["<reason1>", "<reason2>", ...]
    }}

    Rules:
    - "isAnomaly" = true if at least one anomaly is found.
    - "anomalyCount" = total number of distinct anomaly reasons.
    - "reasons" = list of short, specific reasons such as:
        - "Sensitive info requested"
        - "Repeated attempts to extract account details"
        - "Contradictory statements"
        - "Possible scam pattern"
        - "Emotional pressure tactic"
    - Keep reasons short and precise.
    - Do NOT include any extra text.
    """

    user_prompt = f"Transcript: {text} Return JSON only."

    completion = client.beta.chat.completions.parse(
    model="gpt-4o",  
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    response_format=AnomalyEvent,
    )

    response = completion.choices[0].message

    try:
        parsed = json.loads(response.content)

        # Normalize reasons: if it's a single string, convert to list
        if isinstance(parsed.get("reasons"), str):
            parsed["reasons"] = [parsed["reasons"]]

        # Ensure anomalyCount matches the length of reasons
        parsed["anomalyCount"] = len(parsed.get("reasons", []))

        return parsed
    except Exception:
        return {"isAnomaly": False, "anomalyCount": 0, "reasons": []}