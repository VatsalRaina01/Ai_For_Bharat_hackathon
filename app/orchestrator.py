"""Orchestrator — AI-powered continuous conversational agent.

Every message sends the FULL conversation history + user profile + scheme data
to the AI model. The AI handles everything: intent detection, profile extraction,
follow-up questions, scheme matching, and natural conversation — like ChatGPT.
"""
import json
from app.models.schemas import Session, CitizenProfile
from app.config import ENABLE_TTS
from app.integrations.bedrock_client import invoke_model
from app.integrations.language_client import translate_text, text_to_speech
from app.services.scheme_matcher import match_schemes, explain_schemes_text


# ── System prompt — the "brain" of LokSarthi ──
SYSTEM_PROMPT = """You are LokSarthi (लोकसारथी), a friendly AI voice assistant that helps Indian citizens discover government schemes, file RTI applications, and get financial advice.

## Your Personality
- You speak like a helpful village postman or gram sevak — warm, patient, respectful
- Use "आप" (respectful you), "जी" (polite suffix)
- Mix Hindi and English naturally based on the user's language
- Keep responses SHORT (2-4 sentences max) since they will be spoken aloud
- NEVER use markdown formatting (no **, ##, bullets) — speak naturally
- Use simple language a farmer or labourer can understand

## Your Job (on EVERY turn)
1. EXTRACT any personal info the user shares (age, gender, state, occupation, category, income, etc.)
2. If asking about schemes: ask missing info ONE question at a time, conversationally
3. When you have enough info (age, gender, state, occupation at minimum), present matching schemes
4. For RTI/complaints: help draft the application
5. For financial questions: give practical advice, detect scams

## Profile Fields to Extract
age (number), gender (male/female), state, district, occupation (farmer/labourer/vendor/student/homemaker/employed/unemployed), category (general/sc/st/obc/minority), annual_income (number), bpl_status (true/false), disability (true/false), marital_status, land_ownership (true/false), education_level, family_members (number)

## Response Format
You MUST respond with valid JSON only:
{
  "reply": "Your spoken response to the user (short, natural, in their language)",
  "profile_updates": {"field": "value"},
  "intent": "scheme_discovery|rti|financial|greeting|general"
}

## CRITICAL RULES
- reply must be SHORT (spoken aloud by TTS, max 3-4 sentences)
- Do NOT repeat information the user already gave
- Do NOT ask multiple questions at once — ask ONE at a time
- When presenting schemes, name them clearly with benefits
- If user says something unclear, ask for clarification kindly
- Always respond in the same language the user is speaking
"""


def _build_context(session: Session) -> str:
    """Build context string with profile and matched schemes."""
    parts = []

    # User profile
    profile_data = session.profile.to_dict()
    if profile_data:
        parts.append(f"USER PROFILE: {json.dumps(profile_data, ensure_ascii=False)}")
    else:
        parts.append("USER PROFILE: (not yet collected)")

    # Matched schemes (if any)
    if session.matched_schemes:
        parts.append(f"MATCHED SCHEMES: {json.dumps(session.matched_schemes[:5], ensure_ascii=False)}")

    return "\n".join(parts)


def process_message(session: Session, user_message: str) -> dict:
    """
    Process a user message through the AI agent.
    Sends full context to the model on every turn.
    """
    # Add user message to history
    session.add_message("user", user_message)

    # Auto-detect language from user input
    import re
    has_hindi = bool(re.search(r'[\u0900-\u097f]', user_message))
    if has_hindi:
        session.language = "hi"
    elif user_message.strip() and not has_hindi:
        session.language = "en"

    # Extract profile from user message BEFORE calling AI (regex-based)
    _extract_profile_from_text(session.profile, user_message)

    # Match schemes if profile is sufficient (BEFORE AI call, so AI can explain them)
    scheme_info = ""
    if session.profile.completeness_score() >= 0.5:
        matches = match_schemes(session.profile)
        if matches:
            session.matched_schemes = [
                {"name": m["scheme"]["name"], "name_hi": m["scheme"].get("name_hi", m["scheme"]["name"]),
                 "benefit": m["scheme"].get("benefit_amount", ""), "how_to_apply": m["scheme"].get("how_to_apply", ""),
                 "score": m["score"]}
                for m in matches[:5]
            ]
            scheme_info = "\n\nMATCHED SCHEMES (explain these in Hindi to the user):\n" + "\n".join([
                f'{i+1}. {s["name_hi"]} — लाभ: {s["benefit"]} — कैसे आवेदन करें: {s["how_to_apply"]}'
                for i, s in enumerate(session.matched_schemes)
            ])

    # Build the full prompt with context + schemes
    context = _build_context(session)
    full_system = SYSTEM_PROMPT + f"\n\n--- CURRENT CONTEXT ---\n{context}{scheme_info}\n--- END CONTEXT ---"

    # Get conversation history for the model
    history = session.get_recent_history(n=10)

    try:
        # Single AI call with full context including schemes
        raw_response = invoke_model(full_system, user_message, history[:-1])

        # Parse JSON response
        parsed = _parse_ai_response(raw_response)

        # Extract profile updates from AI response
        profile_updates = parsed.get("profile_updates", {})
        _apply_profile_updates(session.profile, profile_updates)

        # Update pillar based on intent
        intent = parsed.get("intent", "general")
        if intent in ("scheme_discovery", "profile_update"):
            session.current_pillar = "scheme_discovery"
        elif intent == "rti":
            session.current_pillar = "rti"
        elif intent == "financial":
            session.current_pillar = "financial"

        response_text = parsed.get("reply", "माफ़ कीजिए, कुछ समस्या हो गई।")

    except Exception as e:
        print(f"AI agent error: {e}")
        # Fallback response
        lang = session.language
        response_text = (
            "माफ़ कीजिए, मुझसे कुछ गलती हो गई। कृपया दोबारा बोलिए।"
            if lang == "hi" else
            "Sorry, something went wrong. Please try again."
        )

    # Log assistant response
    session.add_message("assistant", response_text)

    # Auto-detect response language for TTS
    has_hindi_response = bool(re.search(r'[\u0900-\u097f]', response_text))
    tts_lang = "hi" if has_hindi_response else "en"

    # Generate audio (if TTS enabled)
    audio_base64 = None
    if ENABLE_TTS and len(response_text) < 500:
        try:
            audio_base64 = text_to_speech(response_text[:500], tts_lang)
        except Exception as e:
            print(f"TTS error: {e}")

    return {
        "text": response_text,
        "audio_base64": audio_base64,
        "language": session.language,
        "pillar": session.current_pillar,
        "schemes": session.matched_schemes,
        "session": session,
    }


def _parse_ai_response(raw: str) -> dict:
    """Parse AI response — handles JSON, markdown-wrapped JSON, or plain text."""
    text = raw.strip()

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    if "```" in text:
        try:
            json_str = text.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
            return json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            pass

    # Try finding JSON object in the text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    # Fallback: treat entire response as plain text reply
    return {"reply": text, "profile_updates": {}, "intent": "general"}


def _apply_profile_updates(profile: CitizenProfile, updates: dict):
    """Apply validated profile updates from AI response."""
    for field_name, value in updates.items():
        if not hasattr(profile, field_name) or value is None:
            continue
        # Convert types
        if field_name in ("age", "annual_income", "family_members", "children_count"):
            try:
                value = int(value)
            except (ValueError, TypeError):
                continue
        elif field_name in ("bpl_status", "disability", "land_ownership"):
            if isinstance(value, str):
                value = value.lower() in ("true", "yes", "हाँ", "haan", "1")
        setattr(profile, field_name, value)


def _extract_profile_from_text(profile: CitizenProfile, text: str):
    """Regex-based fallback to extract profile info from natural language."""
    import re
    lower = text.lower().strip()

    # Age: "25 sal", "25 साल", "age 25", "उम्र 25", "I am 25"
    if profile.age is None:
        age_match = re.search(r'(\d{1,3})\s*(?:sal|साल|year|वर्ष|saal|age|उम्र)', lower)
        if not age_match:
            age_match = re.search(r'(?:age|उम्र|umar)\s*(?:is|hai|है)?\s*(\d{1,3})', lower)
        if not age_match:
            # "I am 25" pattern
            age_match = re.search(r'(?:i am|मैं|meri)\s*(\d{1,3})', lower)
        if age_match:
            age = int(age_match.group(1))
            if 1 <= age <= 120:
                profile.age = age

    # Gender
    if profile.gender is None:
        female_words = ["महिला", "female", "woman", "लड़की", "औरत", "stree", "स्त्री", "ladki"]
        male_words = ["पुरुष", "male", "man", "लड़का", "आदमी", "purush", "ladka"]
        if any(w in lower for w in female_words):
            profile.gender = "female"
        elif any(w in lower for w in male_words):
            profile.gender = "male"

    # State
    if profile.state is None:
        states = {
            "बिहार": "bihar", "bihar": "bihar",
            "उत्तर प्रदेश": "uttar pradesh", "uttar pradesh": "uttar pradesh", "up": "uttar pradesh",
            "मध्य प्रदेश": "madhya pradesh", "madhya pradesh": "madhya pradesh", "mp": "madhya pradesh",
            "राजस्थान": "rajasthan", "rajasthan": "rajasthan",
            "महाराष्ट्र": "maharashtra", "maharashtra": "maharashtra",
            "गुजरात": "gujarat", "gujarat": "gujarat",
            "तमिलनाडु": "tamil nadu", "tamil nadu": "tamil nadu",
            "कर्नाटक": "karnataka", "karnataka": "karnataka",
            "पंजाब": "punjab", "punjab": "punjab",
            "हरियाणा": "haryana", "haryana": "haryana",
            "झारखंड": "jharkhand", "jharkhand": "jharkhand",
            "छत्तीसगढ़": "chhattisgarh", "chhattisgarh": "chhattisgarh",
            "उड़ीसा": "odisha", "odisha": "odisha", "orissa": "odisha",
            "केरल": "kerala", "kerala": "kerala",
            "दिल्ली": "delhi", "delhi": "delhi",
            "आंध्र प्रदेश": "andhra pradesh", "andhra pradesh": "andhra pradesh",
            "तेलंगाना": "telangana", "telangana": "telangana",
            "पश्चिम बंगाल": "west bengal", "west bengal": "west bengal",
            "असम": "assam", "assam": "assam",
        }
        for keyword, state_val in states.items():
            if keyword in lower:
                profile.state = state_val
                break

    # Occupation
    if profile.occupation is None:
        occupation_map = {
            "किसान": "farmer", "farmer": "farmer", "kisan": "farmer", "खेती": "farmer",
            "मज़दूर": "labourer", "मजदूर": "labourer", "labourer": "labourer", "labour": "labourer", "mazdoor": "labourer",
            "दुकानदार": "vendor", "vendor": "vendor", "shopkeeper": "vendor", "dukandar": "vendor",
            "छात्र": "student", "student": "student", "chhatra": "student", "विद्यार्थी": "student",
            "गृहिणी": "homemaker", "homemaker": "homemaker", "housewife": "homemaker",
            "नौकरी": "employed", "employed": "employed", "job": "employed", "service": "employed",
            "बेरोज़गार": "unemployed", "unemployed": "unemployed", "berozgar": "unemployed",
        }
        for keyword, occ_val in occupation_map.items():
            if keyword in lower:
                profile.occupation = occ_val
                break

