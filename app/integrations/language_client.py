"""AWS Language services — Translate, Transcribe, Polly for multilingual support."""
import boto3
import base64
import json
import time
import os
from app.config import AWS_REGION, SUPPORTED_LANGUAGES

# AWS clients (reused for Lambda warm starts)
_translate_client = None
_polly_client = None
_transcribe_client = None
_s3_client = None


def get_translate_client():
    global _translate_client
    if _translate_client is None:
        _translate_client = boto3.client("translate", region_name=AWS_REGION)
    return _translate_client


def get_polly_client():
    global _polly_client
    if _polly_client is None:
        _polly_client = boto3.client("polly", region_name=AWS_REGION)
    return _polly_client


# Language code mapping for AWS services
AWS_LANGUAGE_CODES = {
    "hi": "hi",
    "en": "en",
    "ta": "ta",
    "te": "te",
    "bn": "bn",
    "mr": "mr",
    "gu": "gu",
    "kn": "kn",
    "ml": "ml",
    "pa": "pa",
}

# Polly voice IDs for Indian languages
POLLY_VOICES = {
    "hi": "Aditi",       # Hindi - Neural voice
    "en": "Aditi",       # English (India accent)
}


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """
    Translate text between languages using Amazon Translate.

    Args:
        text: Text to translate
        source_lang: Source language code (e.g., "hi")
        target_lang: Target language code (e.g., "en")

    Returns:
        Translated text
    """
    if source_lang == target_lang:
        return text

    if not text or not text.strip():
        return text

    client = get_translate_client()

    try:
        response = client.translate_text(
            Text=text,
            SourceLanguageCode=AWS_LANGUAGE_CODES.get(source_lang, source_lang),
            TargetLanguageCode=AWS_LANGUAGE_CODES.get(target_lang, target_lang),
        )
        return response["TranslatedText"]
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Return original on error


def text_to_speech(text: str, language: str = "hi") -> str:
    """
    Convert text to speech using Amazon Polly.

    Args:
        text: Text to speak
        language: Language code

    Returns:
        Base64-encoded audio (MP3)
    """
    client = get_polly_client()

    voice_id = POLLY_VOICES.get(language, "Aditi")

    try:
        response = client.synthesize_speech(
            Text=text[:3000],  # Polly limit
            OutputFormat="mp3",
            VoiceId=voice_id,
            Engine="standard",
        )

        audio_bytes = response["AudioStream"].read()
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"TTS error: {e}")
        return None


def detect_language(text: str) -> str:
    """
    Detect language of input text using Amazon Comprehend.

    Args:
        text: Input text

    Returns:
        Language code (e.g., "hi", "en")
    """
    try:
        client = boto3.client("comprehend", region_name=AWS_REGION)
        response = client.detect_dominant_language(Text=text[:500])
        languages = response.get("Languages", [])
        if languages:
            detected = languages[0]["LanguageCode"]
            # Map to our supported languages
            if detected in SUPPORTED_LANGUAGES:
                return detected
    except Exception as e:
        print(f"Language detection error: {e}")

    # Default to Hindi
    return "hi"
