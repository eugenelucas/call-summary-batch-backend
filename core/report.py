from core.email_send import send_email
from typing import List
from core.models import State
from io import BytesIO
import io
from core.llm import client 
from functools import lru_cache
from langchain_groq import ChatGroq
import re
import json
from langgraph.graph import StateGraph, END
import os
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
from typing import TypedDict, Optional,Any
from pydantic import BaseModel,Field
from langchain.prompts import ChatPromptTemplate
from mutagen import File


AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")  



def extract_inc_number(state: dict) -> str | None:
    """
    Find 'INC' in state['call_summary'] and state['action_items'] and extract the digits that follow it.
    """
    def find_inc(text: str) -> str | None:
        if not text:  # handle None or empty
            return None

        idx = text.find("INC")
        if idx == -1:
            return None

        i = idx + 3  # move past 'INC'

        # Move forward until the first digit is found
        while i < len(text) and not text[i].isdigit():
            i += 1

        # Collect continuous digits
        digits = []
        while i < len(text) and text[i].isdigit():
            digits.append(text[i])
            i += 1

        if digits:
            return "INC" + "".join(digits)
        return None

    # Search in call_summary
    call_summary = state.get("call_summary") or ""
    inc = find_inc(call_summary)
    if inc:
        return inc

    # Search in action_items
    action_items = state.get("action_items") or []
    for item in action_items:
        for value in item.values():
            if isinstance(value, str):
                inc = find_inc(value)
                if inc:
                    return inc

    return None


def process_email_notifications(result: dict) -> List[str]:
    """
    Processes call results and sends formatted email notifications.
    
    Expected keys in result:
      - sentiment_score: numeric score from the call
      - call_summary: a string summary of the call
      - action_items: either a string or a list of dicts containing tasks
      - customer_email: the customer's email address for confirmation (optional)
      - incident_number: the incident number to include in the customer email (optional)
    """
    import os

    sentiment_score = result.get("sentiment_score", 0)
    agent_email = os.getenv("AGENT_EMAIL")
    manager_email = os.getenv("MANAGER_EMAIL")
    customer_email = result.get("customer_email")
    
    email_sent = []
    
    # Send notifications for negative or positive sentiment
    if sentiment_score <= 5:
        subject = "⚠️ Urgent: Call Needs Attention"
        body = (
            "Dear Manager,\n\n"
            "Please review the following call summary and take appropriate action:\n\n"
            f"{result['call_summary']}\n\n"
            "Thank you,\nSupport Team"
        )
        send_email(subject, manager_email, body)
        email_sent.append("Manager")
        
    elif sentiment_score >= 9:
        subject = "🎉 Great Job!"
        body = (
            "Dear Agent,\n\n"
            "Fantastic performance on the recent call. Here is the call summary:\n\n"
            f"{result['call_summary']}\n\n"
            "Keep up the great work!\n\n"
            "Best regards,\nSupport Team"
        )
        send_email(subject, agent_email, body)
        email_sent.append("Agent")
    
    # Send action item notifications to the agent
    if result.get("action_items"):
        subject = "📌 Action Required: Follow-up Tasks"
        action_items = result.get("action_items")
        if isinstance(action_items, list):
            formatted_items = "\n".join(
                [f"- {item['task']}" if isinstance(item, dict) and "task" in item else f"- {item}" 
                 for item in action_items]
            )
        else:
            formatted_items = action_items
        
        body = (
            "Dear Agent,\n\n"
            "Please address the following action items:\n"
            f"{formatted_items}\n\n"
            "Thank you,\nSupport Team"
        )
        send_email(subject, agent_email, body)
        email_sent.append("Agent (Action Required)")
    
    
    return email_sent

def generate_pdf_report(filename: str,state: State) -> io.BytesIO:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    
    # Define margins and max line width
    left_margin = 50
    right_margin = 50
    max_width = width - left_margin - right_margin
    line_height = 15
    
    def wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> list:
        """Split text into lines that fit within max_width"""
        p.setFont(font_name, font_size)
        # Handle None or empty text
        if not text:
            return [""]
        # Convert to string if not already
        text = str(text)
        # Split long text into multiple lines
        lines = []
        for paragraph in text.split('\n'):
            if paragraph:
                wrapped = simpleSplit(paragraph, font_name, font_size, max_width)
                lines.extend(wrapped)
            else:
                lines.append("")
        return lines
    
    def draw_wrapped_text(text: str, font_name: str = "Helvetica", font_size: int = 12, indent: int = 0):
        nonlocal y
        lines = wrap_text(text, font_name, font_size, max_width - indent)
        for line in lines:
            if y <= 50:  # Add new page if space is low
                p.showPage()
                y = height - 50
                p.setFont(font_name, font_size)
            p.drawString(left_margin + indent, y, line)
            y -= line_height
    
    def draw_title(text: str):
        nonlocal y
        p.setFont("Helvetica-Bold", 14)
        draw_wrapped_text(text, "Helvetica-Bold", 14)
        y -= 5  # Extra space after title
    
    def draw_content(text: str, indent: int = 20):
        p.setFont("Helvetica", 11)
        draw_wrapped_text(text, "Helvetica", 11, indent)
    
    # Title
    p.setFont("Helvetica-Bold", 16)
    draw_wrapped_text("Call Summary Report")
    p.setFont("Helvetica", 12)
    draw_wrapped_text(f"Filename: {filename}")
    y -= 10  # Extra space after header
    
    # Customer Name
    draw_title("Customer Name:")
    draw_content(state.get("Customer_name", "N/A"))
    y -= 10

    # Agent Name
    draw_title("Agent Name:")
    draw_content(state.get("Agent_name", "N/A"))
    y -= 10
    
    # Call Purpose
    draw_title("Call Purpose:")
    purpose_text = state.get("call_purpose", "N/A")
    draw_content(purpose_text)
    y -= 10

    # Summary
    draw_title("Summary:")
    summary_text = state.get("call_summary", "N/A")
    draw_content(summary_text)
    y -= 10
    
    # Speaker Insights
    draw_title("Speaker Insights:")
    insights = state.get("speaker_insights", {})
    if isinstance(insights, dict):
        for speaker, insight in insights.items():
            p.setFont("Helvetica-Bold", 11)
            draw_wrapped_text(f"{speaker}:", "Helvetica-Bold", 11, 20)
            p.setFont("Helvetica", 11)
            draw_content(insight or "No insights available", 40)
            y -= 5
    else:
        draw_content("No insights available")
    y -= 10
    
    # Action Items
    draw_title("Action Items:")
    action_items = state.get("action_items", [])
    if action_items:
        if isinstance(action_items, list):
            for i, item in enumerate(action_items, 1):
                if isinstance(item, dict) and "task" in item:
                    task_text = f"{i}. {item['task']}"
                else:
                    task_text = f"{i}. {str(item)}"
                draw_content(task_text)
                y -= 5
        else:
            draw_content(str(action_items))
    else:
        draw_content("None")
    y -= 10
    
    # Call-outs (if available)
    if state.get("call_outs"):
        draw_title("Key Call-outs:")
        for callout in state.get("call_outs", []):
            time_sec = callout.get("time_sec", "?")
            label = callout.get("label", "")
            description = callout.get("description", "")
            
            p.setFont("Helvetica-Bold", 11)
            draw_wrapped_text(f"[{time_sec}s] {label}:", "Helvetica-Bold", 11, 20)
            p.setFont("Helvetica", 11)
            draw_content(description, 40)
            y -= 5
    
    # Agent Rating
    draw_title("Agent Rating:")
    draw_content(f"{state.get('Agent_rating', 'N/A')}/10")
    y -= 10

    # Sentiment
    draw_title("Sentiment:")
    sentiment_text = state.get("sentiment", "N/A")
    draw_content(sentiment_text)
    y -= 10
    
    # Sentiment Score
    draw_title("Sentiment Score:")
    draw_content(str(state.get("sentiment_score", "N/A")))
    y -= 10
    p.save()
    buffer.seek(0)
    return buffer

# LLM loader with caching (only OpenAI and ChatGroq)
@lru_cache(maxsize=1)
def load_llm(model_option: str):
    if model_option == "AzureOpenAI":
        return client
        #ChatOpenAI(model="gpt-4o-mini")
    elif model_option == "ChatGroq":
        return ChatGroq(model_name="llama-3.3-70b-versatile")
    else:
        raise ValueError(f"Unsupported model option: {model_option}")

# Add these utility functions
def clean_response(response_text: str) -> str:
    """
    Remove markdown formatting (e.g., triple backticks) from the model's response.
    """
    response_text = response_text.strip()
    fence_pattern = r"^```(?:json)?\s*(.*)\s*```$"
    match = re.search(fence_pattern, response_text, re.DOTALL)
    if match:
        response_text = match.group(1).strip()
    return response_text

# Modify the analyze_call_chunks function
def analyze_call_chunks(chunks):
    """
    Returns list of call-outs even on partial failure
    """
    try:
        transcript = "\n".join(
            [f"{chunk['time_sec']}s: {chunk['text']} (Sentiment: {chunk['sentiment']})" 
             for chunk in chunks]
        )
        
        prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant that analyzes call transcription chunks to identify major call-outs. "
                "Provide output as a JSON list of objects with keys: 'time_sec', 'label', and 'description'. "
                "Example: {{\"time_sec\": 94, \"label\": \"High Frustration\", \"description\": \"Customer expresses frustration over repeated issues.\"}}"
            ),
            ("human", "Use the following transcription for analysis:\n\n{transcript}"),
        ]
    )
        
        chain = prompt | client
        response = chain.invoke({"transcript": transcript})
        response_text = clean_response(response.content)
        
        # Add robust JSON parsing
        try:
            results = json.loads(response_text)
            if not isinstance(results, list):
                raise ValueError("Response is not a list")
                
            # Validate individual items
            valid_results = []
            for item in results:
                if all(k in item for k in ("time_sec", "label", "description")):
                    valid_results.append({
                        "time_sec": int(float(item["time_sec"])),
                        "label": str(item["label"]),
                        "description": str(item["description"])
                    })
            #print (valid_results)
            return valid_results
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {str(e)}")
            return []
            
    except Exception as e:
        print(f"Analysis failed: {str(e)}")
        return []
# === BATCH SENTIMENT ANALYSIS ===
def get_batch_sentiment_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", "Analyze sentiment for these segments separated by '|'. Return JSON array of 'positive','neutral','negative' in order"),
        ("human", "Segments: {segments}")
    ])
# Create processing pipeline per request

def create_pipeline(llm) -> any:
    def transcribe_node(state: State) -> State:
        result = transcribe_audio_openai(state["audio_path"])

        transcription, segments, duration = result['text'], result.get('segments', []), result["duration"]
        batch = get_batch_sentiment_prompt() | load_llm('AzureOpenAI')
        resp = batch.invoke({'segments': ' | '.join([s.text for s in segments])})
        try:
            sentiments = json.loads(resp.content)
        except:
            sentiments = ['neutral'] * len(segments)
        chunks = [
            {'time_sec': round(s.start, 2), 'text': s.text.strip(), 'sentiment': sentiments[i] if i < len(sentiments) else 'neutral'}
            for i, s in enumerate(segments)
        ]
        
        return {**state, "transcription": transcription, "sentiment_chunks": chunks,"audio_duration":duration}

    def summarize_node(state: State) -> State:
        prompt = get_summarize_text_prompt()
        chain = prompt | llm
        response = chain.invoke({"transcription": state["transcription"]})
        parsed = clean_and_parse_json(response.content)
        if parsed:
            return {
                **state,
                "call_summary": parsed.get("summary", "No summary available."),
                "sentiment": parsed.get("sentiment", "Not detected"),
                "sentiment_score": parsed.get("sentiment_score", 0),
                "call_purpose": parsed.get("call_purpose", "Not detected"),
                "speaker_insights": parsed.get("speaker_insights"),
                "action_items": parsed.get("action_items"),
                "Agent_rating": parsed.get("Agent_rating"),
                "Customer_name": parsed.get("Customer_name", "Not detected"),
                "Agent_name": parsed.get("Agent_name", "Not detected")
            }
        return {**state, "call_summary": "Error parsing response.", "sentiment": "", "sentiment_score": 0,
                "call_purpose": "", "speaker_insights": None, "action_items": None,"Agent_rating": 0,"Customer_name":"", "Agent_name":""}

    def analyze_callouts_node(state: State) -> State:
        #print("\n=== ENTERING CALLOUTS NODE ===")
        chunks = state.get("sentiment_chunks", [])
        #print(f"Received {len(chunks)} chunks for analysis")
        
        analysis = analyze_call_chunks(chunks)
        #print(f"Raw analysis results: {analysis}")
        
        # Convert and validate results
        validated = []
        for item in analysis if isinstance(analysis, list) else []:
            try:
                validated.append({
                    "time_sec": int(item["time_sec"]),
                    "label": str(item["label"]),
                    "description": str(item["description"])
                })
            except (KeyError, TypeError) as e:
                print(f"Skipping invalid item: {e}")
        
        #print(f"Validated callouts: {validated}")
        return {**state, "call_outs": validated}

    # Build graph with VERBOSE connection logging
    graph = StateGraph(State)
    graph.add_node("transcribe", transcribe_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("analyze_callouts", analyze_callouts_node)
    
    #print("\n=== GRAPH CONNECTIONS ===")
    graph.add_edge("transcribe", "summarize")
    #print("Connected transcribe → summarize")
    graph.add_edge("summarize", "analyze_callouts")
    #print("Connected summarize → analyze_callouts")
    graph.add_edge("analyze_callouts", END)
    #print("Connected analyze_callouts → END")
    
    graph.set_entry_point("transcribe")
    return graph.compile()

@lru_cache(maxsize=100)
def transcribe_audio_openai(audio_file_path: str) -> dict:
    """
    Transcribes the audio file using Azure OpenAI Whisper and returns both full text and segments with timestamps.
    Returns:
        {
            "text": str,
            "segments": list of {
                "start": float,
                "end": float,
                "text": str
            }
        }
    """
    client = AzureOpenAI(
        api_key=os.getenv("OPENAI_KEY_W"),  
        api_version="2024-02-01",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_W")
    )
    deployment_id = "whispernew"
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        blob_client = container_client.get_blob_client(audio_file_path)

        download_stream = blob_client.download_blob()
        audio_stream = BytesIO(download_stream.readall())
        audio_stream.name = "audio.mp3" 
        transcription = client.audio.transcriptions.create(
            model=deployment_id,
            file=audio_stream,
            response_format="verbose_json"
        ) 
         
        audio_stream.seek(0)
        # auto-detect format (mp3, wav, flac, ogg, etc.)
        audio = File(audio_stream)

        if audio is not None and audio.info is not None:
            duration_seconds = int(audio.info.length)
        else:
            duration_seconds = 0
        return {
            "text": transcription.text,         # full transcription
            "segments": transcription.segments,  # sentence-level timestamps from Whisper
            "duration":duration_seconds
        }

    except Exception as e:
        raise Exception(f"Error transcribing audio: {str(e)}")


# Prompt for summarization
def get_summarize_text_prompt() -> ChatPromptTemplate:
    systemContent = '''
You are an assistant that generates concise, insightful, and professional call summaries in JSON format. Your task is to analyze the provided transcription and extract key details with a specific focus on capturing not only the literal words but also the underlying tone, emotional nuances, and customer sentiment such as frustration, annoyance, and any other subtle emotional indicators. Ensure that your analysis is based on both the textual content and the overall call context.

The JSON output must include the following fields without any change in their format:

- "summary": A concise summary of the call, capturing all key points discussed.
- "sentiment": An aspect-based sentiment analysis narrative that integrates tone and emotional indicators, including but not limited to frustration, calmness, or enthusiasm. This should encompass both explicit language cues and contextual interpretations.
- "sentiment_score": A numeric integer overall sentiment score (1-10) that reflects the cumulative sentiment of the call, factoring in words used, tone, and emotional nuances.
- "call_purpose": The main objective of the call, derived from the discussion.
- "speaker_insights": A dictionary with two keys, "Customer" and "Agent". Each key should have a descriptive string insight that captures not only what was spoken, but also the inferred emotional state (e.g., customer tone, frustration, annoyance; agent's tone, empathy, professionalism) observed during the call. Use both direct content and overall call dynamics to inform your insights.
- "Agent_rating": Based upon the conversation and speaker insights, rate the performance of Agent out of 10, for example if he talks nicely, behave properly give him rating 8-10,if his tone was not appropriate, he didnt show empathy to the customer in such scenarios give him ratings below 4. Use your intelligence to observe agent performance and rate him out of 10."
- "Customer_name": Based upon the conversation fetch Customer Name. if Customer name is not mentioned then return NA."
- "Agent_name": Based upon the conversation fetch Agent Name. if Agent name is not mentioned then return NA."
- "action_items": A list of follow-up action items that has been discussed during the call, that need to undertaken by the Agent in the future in following format:
  [{{"task"}}: "<description>"]

Here is the transcription: "{transcription}"

Return the response in JSON format only, without any extra text.
'''
    messages = [("system", systemContent), ("human", "{transcription}")]
    return ChatPromptTemplate.from_messages(messages)


def get_sentiment_prompt_template() -> ChatPromptTemplate:
    system_content = '''
        You are a highly experienced sentiment analysis assistant specializing in call transcript segments. When evaluating a segment, consider not only the explicit words but also the overall tone, context, and any subtle emotional cues. This includes, but is not limited to, frustration, annoyance, urgency, disappointment, satisfaction, calmness, or enthusiasm. Specifically:
        - If the segment expresses frustration, anger, disappointment, or urgency through either explicit language or tone, classify it as "negative".
        - If the segment conveys satisfaction, optimism, encouragement, or a positive, upbeat tone, classify it as "positive".
        - If the segment is informational, neutral, or does not clearly lean toward either extreme, classify it as "neutral".
        Your response must be exactly one word: "positive", "neutral", or "negative", with no additional commentary or explanation.
        '''
    human_content = 'Segment: "{segment_text}"'
    messages = [("system", system_content), ("human", human_content)]
    return ChatPromptTemplate.from_messages(messages)


# JSON cleaning utility
def clean_and_parse_json(response_text: str) -> Optional[dict]:
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return None
    except json.JSONDecodeError:
        return None
