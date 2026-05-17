from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

VOICE_IDS = {
    "The Ice Queen": "21m00Tcm4TlvDq8ikWAM",
    "The Distracted Barista": "AZnzlk1XvdvUeBnXmlld",
    "The Group Dynamic": "EXAVITQu4vr4xnSDxMaL",
    "default": "21m00Tcm4TlvDq8ikWAM"
}

class TTSRequest(BaseModel):
    text: str
    character: str = "default"
    language: str = "English"

@app.get("/health")
def health():
    return {"status": "ok", "service": "AURA Voice", "has_key": bool(ELEVENLABS_API_KEY)}

@app.post("/tts")
async def text_to_speech(req: TTSRequest):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not set")
    
    voice_id = VOICE_IDS.get(req.character, VOICE_IDS["default"])
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": req.text[:500],
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"ElevenLabs error {response.status_code}: {response.text}"
            )
        
        audio_b64 = base64.b64encode(response.content).decode("utf-8")
        return {"audio": audio_b64, "format": "mp3"}

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not set")
    
    content = await file.read()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            files={"file": (file.filename, content, file.content_type)},
            data={"model_id": "scribe_v1"},
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"STT error {response.status_code}: {response.text}"
            )
        
        result = response.json()
        return {"transcript": result.get("text", "")}
