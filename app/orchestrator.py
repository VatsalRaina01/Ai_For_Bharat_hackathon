"""Orchestrator — Central brain that routes user requests to the correct service pillar."""
import json
from app.models.schemas import Session, CitizenProfile
from app.integrations.bedrock_client import detect_intent, generate_response
from app.integrations.language_client import translate_text, text_to_speech
from app.services.scheme_matcher import match_schemes, explain_schemes, get_profiling_question
from app.services.rti_assistant import handle_rti_request
from app.services.financial_advisor import handle_financial_query


# Profiling questions in different languages
PROFILE_QUESTIONS = {
    "age": {
        "hi": "🙏 आपकी उम्र कितनी है?",
        "en": "🙏 What is your age?",
    },
    "gender": {
        "hi": "आप पुरुष हैं या महिला?",
        "en": "Are you male or female?",
    },
    "state": {
        "hi": "आप किस राज्य में रहते हैं?",
        "en": "Which state do you live in?",
    },
    "occupation": {
        "hi": "आप क्या काम करते हैं? (किसान, मज़दूर, दुकानदार, छात्र, गृहिणी...)",
        "en": "What is your occupation? (farmer, labourer, vendor, student, homemaker...)",
    },
    "category": {
        "hi": "आपकी श्रेणी क्या है? (सामान्य, SC, ST, OBC, अल्पसंख्यक)",
        "en": "What is your category? (General, SC, ST, OBC, Minority)",
    },
    "income": {
        "hi": "आपकी सालाना आय (कमाई) लगभग कितनी है?",
        "en": "What is your approximate annual income?",
    },
    "marital_status": {
        "hi": "आपकी वैवाहिक स्थिति क्या है? (विवाहित, अविवाहित, विधवा/विधुर)",
        "en": "What is your marital status? (married, single, widowed)",
    },
    "bpl": {
        "hi": "क्या आपके पास BPL (गरीबी रेखा से नीचे) कार्ड है?",
        "en": "Do you have a BPL (Below Poverty Line) card?",
    },
}


GREETING_RESPONSES = {
    "hi": """🙏 नमस्ते! मैं **लोकसारथी** हूँ — आपका AI सहायक।

मैं आपकी 3 तरह से मदद कर सकता हूँ:

🏛️ **सरकारी योजनाएँ** — बताइए अपने बारे में, मैं बताऊँगा कौन सी योजनाएँ आपके लिए हैं
📝 **RTI / शिकायत** — अपनी समस्या बताइए, मैं RTI आवेदन बना दूँगा
💰 **लोन / पैसा सलाह** — लोन, बचत, या धोखाधड़ी के बारे में पूछिए

बस बोलिए या लिखिए — मैं हिंदी, English, और कई भारतीय भाषाओं में समझता हूँ! 🇮🇳""",

    "en": """🙏 Namaste! I am **LokSarthi** — your AI assistant.

I can help you in 3 ways:

🏛️ **Government Schemes** — Tell me about yourself, I'll find schemes you're eligible for
📝 **RTI / Complaint** — Describe your problem, I'll draft an RTI application
💰 **Loan / Financial Advice** — Ask about loans, savings, or fraud protection

Just speak or type — I understand Hindi, English, and many Indian languages! 🇮🇳""",
}


def process_message(session: Session, user_message: str) -> dict:
    """
    Process a user message through the orchestrator pipeline.

    Args:
        session: Current user session
        user_message: User's input text

    Returns:
        {
            "text": response text,
            "audio_base64": base64 audio (or None),
            "language": detected/used language,
            "pillar": active service pillar,
            "schemes": matched schemes (if any),
            "session": updated session
        }
    """
    language = session.language

    # Step 1: Detect intent and extract profile info
    intent_result = detect_intent(user_message, session.get_recent_history())

    intent = intent_result.get("intent", "greeting")
    profile_updates = intent_result.get("profile_updates", {})
    detected_lang = intent_result.get("language_detected", language)

    # Update session language if detected
    if detected_lang and detected_lang in ["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]:
        session.language = detected_lang
        language = detected_lang

    # Step 2: Update citizen profile with extracted info
    for field, value in profile_updates.items():
        if hasattr(session.profile, field) and value is not None:
            setattr(session.profile, field, value)

    # Step 3: Log user message
    session.add_message("user", user_message)

    # Step 4: Route to correct pillar
    response_text = ""

    if intent == "greeting":
        response_text = GREETING_RESPONSES.get(language, GREETING_RESPONSES["en"])
        session.current_pillar = "greeting"

    elif intent in ["scheme_discovery", "profile_update"]:
        session.current_pillar = "scheme_discovery"
        response_text = _handle_scheme_discovery(session, user_message, language)

    elif intent == "rti":
        session.current_pillar = "rti"
        response_text = handle_rti_request(user_message, session.profile, language)

    elif intent == "financial":
        session.current_pillar = "financial"
        response_text = handle_financial_query(user_message, session.profile, language)

    else:
        # Default: check if we're in the middle of a flow
        if session.current_pillar == "scheme_discovery":
            response_text = _handle_scheme_discovery(session, user_message, language)
        elif session.current_pillar == "rti":
            response_text = handle_rti_request(user_message, session.profile, language)
        elif session.current_pillar == "financial":
            response_text = handle_financial_query(user_message, session.profile, language)
        else:
            response_text = GREETING_RESPONSES.get(language, GREETING_RESPONSES["en"])

    # Step 5: Log assistant response
    session.add_message("assistant", response_text)

    # Step 6: Generate audio (only for short responses to save cost)
    audio_base64 = None
    if len(response_text) < 500:
        try:
            # For non-Hindi/English, translate to Hindi for TTS
            tts_text = response_text[:500]
            tts_lang = language if language in ["hi", "en"] else "hi"
            if language not in ["hi", "en"]:
                tts_text = translate_text(response_text[:300], language, "hi")
            audio_base64 = text_to_speech(tts_text, tts_lang)
        except Exception as e:
            print(f"TTS error: {e}")

    return {
        "text": response_text,
        "audio_base64": audio_base64,
        "language": language,
        "pillar": session.current_pillar,
        "schemes": session.matched_schemes,
        "session": session,
    }


def _handle_scheme_discovery(session: Session, user_message: str, language: str) -> str:
    """Handle scheme discovery flow with progressive profiling."""

    # Check if profile is complete enough for matching
    next_question = get_profiling_question(session.profile)

    if next_question and session.profile.completeness_score() < 0.5:
        # Need more info — ask the next profiling question
        question = PROFILE_QUESTIONS.get(next_question, {}).get(language, PROFILE_QUESTIONS[next_question]["en"])

        if session.profile.completeness_score() == 0:
            # First question — add context
            intro = {
                "hi": "चलिए, आपके लिए सही योजनाएँ ढूंढते हैं! बस कुछ सवालों के जवाब दीजिए:\n\n",
                "en": "Let me find the right schemes for you! Just answer a few questions:\n\n",
            }
            return intro.get(language, intro["en"]) + question
        else:
            return f"धन्यवाद! 👍 अगला सवाल:\n\n{question}" if language == "hi" else f"Thank you! 👍 Next question:\n\n{question}"

    else:
        # Profile is sufficient — run matching
        matches = match_schemes(session.profile)
        session.matched_schemes = [
            {"name": m["scheme"]["name"], "benefit": m["scheme"]["benefit_amount"], "score": m["score"]}
            for m in matches
        ]

        # Generate AI explanation
        return explain_schemes(matches, session.profile, language)
