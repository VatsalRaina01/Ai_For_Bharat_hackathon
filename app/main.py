"""LokSarthi — FastAPI Application + Lambda Handler."""
import json
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from app.orchestrator import process_message
from app.models.schemas import Session
from app.integrations.dynamo_client import get_session, save_session, delete_session

# FastAPI app
app = FastAPI(
    title="LokSarthi API",
    description="AI-powered voice-first multilingual citizen services platform",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "LokSarthi", "version": "1.0.0"}


@app.post("/api/chat")
async def chat(request: Request):
    """
    Main chat endpoint — handles text-based conversation.

    Request body:
    {
        "message": "user's message text",
        "session_id": "optional session ID",
        "language": "optional language code"
    }

    Response:
    {
        "text": "AI response",
        "audio_base64": "base64 encoded MP3 audio or null",
        "language": "detected/used language",
        "pillar": "active service pillar",
        "session_id": "session UUID",
        "schemes": [matched schemes if any]
    }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON body"}
        )

    message = body.get("message", "").strip()
    if not message:
        return JSONResponse(
            status_code=400,
            content={"error": "Message is required"}
        )

    session_id = body.get("session_id", str(uuid.uuid4()))
    language = body.get("language")

    # Get or create session
    session = get_session(session_id)

    # Override language if provided
    if language:
        session.language = language

    # Process message through orchestrator
    result = process_message(session, message)

    # Save updated session
    updated_session = result.pop("session")
    save_session(updated_session)

    # Return response
    return JSONResponse(content={
        "text": result["text"],
        "audio_base64": result.get("audio_base64"),
        "language": result["language"],
        "pillar": result["pillar"],
        "session_id": session_id,
        "schemes": result.get("schemes", []),
    })


@app.post("/api/voice")
async def voice_input(request: Request):
    """
    Voice input endpoint — accepts audio, transcribes, processes, returns audio response.

    Request body:
    {
        "audio_base64": "base64 encoded audio",
        "session_id": "optional session ID",
        "language": "optional language code for ASR"
    }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    audio_base64 = body.get("audio_base64")
    if not audio_base64:
        return JSONResponse(status_code=400, content={"error": "audio_base64 is required"})

    session_id = body.get("session_id", str(uuid.uuid4()))
    language = body.get("language", "hi")

    # For now, return a message asking to use text input
    # Full Transcribe integration requires S3 upload + async transcription
    return JSONResponse(content={
        "text": "Voice input received. Please use text input for now — voice transcription will be available soon.",
        "audio_base64": None,
        "language": language,
        "pillar": "greeting",
        "session_id": session_id,
        "schemes": [],
        "note": "Voice transcription via Amazon Transcribe coming soon"
    })


@app.get("/api/schemes")
async def list_schemes():
    """List all available government schemes."""
    import os
    schemes_path = os.path.join(os.path.dirname(__file__), "data", "schemes", "central_schemes.json")
    with open(schemes_path, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    return JSONResponse(content={
        "total": len(schemes),
        "schemes": [
            {
                "id": s["scheme_id"],
                "name": s["name"],
                "name_hi": s.get("name_hi", ""),
                "benefit": s["benefit_amount"],
                "ministry": s.get("ministry", ""),
                "type": s.get("benefit_type", ""),
                "apply_url": s.get("apply_url", ""),
            }
            for s in schemes
        ]
    })


@app.delete("/api/session/{session_id}")
async def delete_user_session(session_id: str):
    """Delete a session — right to erasure (DPDP Act compliance)."""
    delete_session(session_id)
    return JSONResponse(content={"status": "deleted", "session_id": session_id})


# Lambda handler via Mangum
handler = Mangum(app, lifespan="off")
