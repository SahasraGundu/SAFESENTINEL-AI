from __future__ import annotations

import io

from utils.llm import get_client

WHISPER_MODEL = "whisper-large-v3-turbo"


def voice_available() -> bool:
    return get_client() is not None


def transcribe_audio(audio_bytes: bytes, filename: str = "recording.webm") -> tuple[str | None, str | None]:
    """Returns (transcript, error_message). Exactly one will be None."""
    client = get_client()
    if client is None:
        return None, "Voice transcription needs GROQ_API_KEY — add it to .env to enable this."
    if not audio_bytes:
        return None, "No audio was captured. Try recording again."
    try:
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = filename
        result = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=file_obj,
            response_format="text",
        )
        text = result if isinstance(result, str) else getattr(result, "text", "")
        text = (text or "").strip()
        if not text:
            return None, "Transcription came back empty — the recording may have been too short or silent."
        return text, None
    except Exception as e:
        return None, f"Transcription failed: {e}"