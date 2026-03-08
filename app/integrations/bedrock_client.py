"""Amazon Bedrock client — core AI engine using Amazon Nova Micro."""
import json
import boto3
from botocore.config import Config as BotoConfig
from app.config import AWS_REGION, BEDROCK_MODEL_ID, BEDROCK_MAX_TOKENS, BEDROCK_TEMPERATURE

# Initialize Bedrock client with timeout (reused across invocations)
_bedrock_client = None


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        cfg = BotoConfig(connect_timeout=10, read_timeout=30, retries={"max_attempts": 1})
        _bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION, config=cfg)
    return _bedrock_client


def invoke_model(system_prompt: str, user_message: str, conversation_history: list = None) -> str:
    """
    Invoke the configured Bedrock model with system prompt and conversation context.

    Supports Amazon Nova (default) and Claude API formats automatically.

    Args:
        system_prompt: System-level instructions
        user_message: Current user message
        conversation_history: Previous messages [{role, content}]

    Returns:
        Model's response text
    """
    client = get_bedrock_client()
    model_id = BEDROCK_MODEL_ID

    # Build messages with history for context
    messages = []
    if conversation_history:
        for msg in conversation_history[-2:]:  # Last 2 messages — saves input tokens
            content = msg["content"]
            # Nova expects content as list of text blocks
            if isinstance(content, str):
                content = [{"text": content}]
            messages.append({"role": msg["role"], "content": content})

    # Add current user message
    messages.append({"role": "user", "content": [{"text": user_message}]})

    # Use Amazon Nova / Converse API format
    if "claude" in model_id or "anthropic" in model_id:
        # Claude format (fallback if user switches back)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": BEDROCK_MAX_TOKENS,
            "temperature": BEDROCK_TEMPERATURE,
            "system": system_prompt,
            "messages": [{"role": m["role"], "content": m["content"][0]["text"]
                          if isinstance(m["content"], list) else m["content"]}
                         for m in messages],
        })
        response = client.invoke_model(
            modelId=model_id, contentType="application/json",
            accept="application/json", body=body,
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    else:
        # Amazon Nova format (Converse API)
        body = json.dumps({
            "system": [{"text": system_prompt}],
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": BEDROCK_MAX_TOKENS,
                "temperature": BEDROCK_TEMPERATURE,
            },
        })
        response = client.invoke_model(
            modelId=model_id, contentType="application/json",
            accept="application/json", body=body,
        )
        result = json.loads(response["body"].read())
        return result["output"]["message"]["content"][0]["text"]


# Keep backward-compatible alias
invoke_claude = invoke_model


# ── Free local keyword classifier (saves Bedrock calls for obvious messages) ──
_GREETING_KEYWORDS = {
    "namaste", "hello", "hi", "namaskar", "hey", "helo",
    "नमस्ते", "हैलो", "शुरू", "start", "help", "मदद"
}
_SCHEME_KEYWORDS = {
    "scheme", "yojana", "योजना", "subsidy", "sarkar",
    "government", "benefit", "eligible", "apply", "form",
    "सब्सिडी", "सरकार", "लाभ", "आवेदन",
    "स्कीम", "किसान", "फार्मर", "farmer", "pension", "पेंशन",
    "राशन", "ration", "awas", "आवास", "housing", "बीमा",
}
_RTI_KEYWORDS = {
    "rti", "complaint", "grievance", "shikayat", "शिकायत",
    "application", "appeal", "officer", "department", "notice"
}
_FINANCIAL_KEYWORDS = {
    "loan", "ऋण", "लोन", "interest", "bank", "mudra",
    "savings", "fraud", "scam", "insurance", "kcc", "ब्याज",
    "पैसा", "money", "emi", "सहूकार", "sahukar",
}


def _quick_classify(text: str) -> dict | None:
    """Return a result dict without calling Bedrock if intent is obvious."""
    lower = text.lower().strip()

    # Detect language hint cheaply
    lang = "hi" if any("\u0900" <= c <= "\u097f" for c in text) else "en"

    def _hits(keywords: set) -> bool:
        """True if any keyword is a substring of the message (handles plurals/inflections)."""
        return any(kw in lower for kw in keywords)

    # Pure greeting (very short or only greeting words)
    if len(lower) < 30 and (_hits(_GREETING_KEYWORDS) or lower in {"?", ".", ""}):
        return {"intent": "greeting", "profile_updates": {}, "language_detected": lang}

    if _hits(_RTI_KEYWORDS):
        return {"intent": "rti", "profile_updates": {}, "language_detected": lang}

    if _hits(_FINANCIAL_KEYWORDS):
        return {"intent": "financial", "profile_updates": {}, "language_detected": lang}

    if _hits(_SCHEME_KEYWORDS):
        return {"intent": "scheme_discovery", "profile_updates": {}, "language_detected": lang}

    return None  # Unclear — fall through to Bedrock


def detect_intent(user_message: str, conversation_history: list = None) -> dict:
    """
    Detect user intent and extract profile information from the message.
    Tries a free local keyword classifier first; only calls Bedrock when needed.

    Returns:
        {
            "intent": "scheme_discovery" | "rti" | "financial" | "greeting" | "profile_update",
            "profile_updates": {field: value},
            "language_detected": "hi" | "en" | ...
        }
    """
    # Try local classifier first — zero cost
    quick = _quick_classify(user_message)
    if quick is not None:
        return quick

    # Fall back to Bedrock for ambiguous messages
    system_prompt = (
        "You are LokSarthi's intent classifier. Analyze the message and return JSON only.\n"
        "INTENTS: greeting | scheme_discovery | rti | financial | profile_update\n"
        "PROFILE FIELDS: age(int), gender, state, occupation, category, "
        "annual_income(int), bpl_status(bool), disability(bool), marital_status, "
        "land_ownership(bool), education_level, family_members(int), children_count(int)\n"
        "Reply ONLY with valid JSON: "
        '{"intent": "...", "profile_updates": {...}, "language_detected": "hi|en|..."}'
    )

    try:
        response = invoke_model(system_prompt, user_message, conversation_history)
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(clean)
    except Exception as e:
        print(f"Bedrock intent detection failed, using fallback: {e}")
        # Smart fallback — guess intent from language
        lang = "hi" if any("\u0900" <= c <= "\u097f" for c in user_message) else "en"
        return {"intent": "scheme_discovery", "profile_updates": {}, "language_detected": lang}


def generate_response(system_prompt: str, user_message: str, context_data: str = "",
                       conversation_history: list = None) -> str:
    """
    Generate a contextual response with optional data context.

    Args:
        system_prompt: Instructions for this specific pillar
        user_message: User's query
        context_data: Relevant scheme/RTI/financial data to include
        conversation_history: Previous messages
    """
    full_prompt = system_prompt
    if context_data:
        full_prompt += f"\n\n--- REFERENCE DATA ---\n{context_data}\n--- END DATA ---"

    return invoke_model(full_prompt, user_message, conversation_history)
