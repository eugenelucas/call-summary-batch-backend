from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os 
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from api.routes import api_router

try:
    from pydub import AudioSegment
    from pydub.utils import which
    ffmpeg_path = which("ffmpeg") or which("ffmpeg.exe") or os.getenv("FFMPEG_PATH")
    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
    else:
        print("Warning: ffmpeg not found; please ensure ffmpeg is on PATH or set FFMPEG_PATH to its location.")
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    PYDUB_AVAILABLE = False

# Load environment variables
load_dotenv(override=True)

app = FastAPI(
    title="Call Summary & Insights API",
    description="API to transcribe audio, generate call summaries, sentiment analysis, graphing, and send notifications",
    version="1.3.1"
)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("✅ CORS middleware is active")


class CORSFallbackMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            response = await call_next(request)
        except Exception as e:
            print("❌ Error in request:", str(e))
            response = Response("Internal server error" + str(e), status_code=500)
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "*")
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

app.add_middleware(CORSFallbackMiddleware)
app.include_router(api_router)


















if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))


