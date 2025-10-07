from fastapi import APIRouter
from fastapi import HTTPException, UploadFile, File
from fastapi import Query 
from dbs.audio import get_audio_files
from dbs.audio import insert_audio_metadata
from fastapi.responses import JSONResponse
from core.blob import upload_audio_to_blob

router = APIRouter()

@router.get("/audio-files", response_model=dict,tags=["Audio files"])
def list_audio_files():
    return get_audio_files()


@router.options("/{full_path:path}", tags=["Audio files"])
async def preflight_handler(full_path: str):
    return JSONResponse(content={"message": "Preflight OK"})

@router.post("/upload-audio/", tags=["Audio files"])
async def upload_audio(file: UploadFile = File(...)):
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only audio files are allowed.")

    try:
        blob_url = upload_audio_to_blob(file)
        insert_audio_metadata(file.filename, file.filename)

        return {
            "filename": file.filename,
            "url": blob_url,
            "message": "File uploaded and metadata saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")