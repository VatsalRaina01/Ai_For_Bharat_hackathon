"""Amazon Bedrock client for Claude 3 Haiku — core AI engine."""
import json
import boto3
from app.config import AWS_REGION, BEDROCK_MODEL_ID, BEDROCK_MAX_TOKENS, BEDROCK_TEMPERATURE

# Initialize Bedrock client (reused across invocations for Lambda warm starts)
_bedrock_client = None


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _bedrock_client


def invoke_claude(system_prompt: str, user_message: str, conversation_history: list = None) -> str:
    """
    Invoke Claude 3 Haiku via Bedrock with system prompt and conversation context.

    Args:
        system_prompt: System-level instructions for Claude
        user_message: Current user message
        conversation_history: Previous messages [{role, content}]

    Returns:
        Claude's response text
    """
    client = get_bedrock_client()

    # Build messages array with history for context
    messages = []
    if conversation_history:
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": BEDROCK_MAX_TOKENS,
        "temperature": BEDROCK_TEMPERATURE,
        "system": system_prompt,
        "messages": messages,
    })

    response = client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def detect_intent(user_message: str, conversation_history: list = None) -> dict:
    """
    Detect user intent and extract profile information from the message.

    Returns:
        {
            "intent": "scheme_discovery" | "rti" | "financial" | "greeting" | "profile_update",
            "profile_updates": {field: value},
            "language_detected": "hi" | "en" | ...
        }
    """
    system_prompt = """You are LokSarthi's intent classifier. Analyze the user's message and return a JSON response.

INTENTS:
- "greeting": User is greeting, asking what the service does, or starting a conversation
- "scheme_discovery": User wants to find government schemes they're eligible for
- "rti": User wants to file an RTI application, grievance, or complaint against a government department
- "financial": User asks about loans, interest rates, savings, scams, or financial advice
- "profile_update": User is providing personal information (age, occupation, location, etc.)

PROFILE EXTRACTION:
Extract any personal details mentioned. Map to these fields:
- age (integer)
- gender ("male"/"female"/"other")
- state (Indian state name in English)
- district (district name)
- occupation ("farmer"/"labourer"/"vendor"/"student"/"homemaker"/"unemployed"/"other")
- category ("general"/"sc"/"st"/"obc"/"minority")
- annual_income (integer in INR)
- bpl_status (true/false)
- disability (true/false)
- marital_status ("married"/"widowed"/"single"/"divorced")
- land_ownership (true/false)
- education_level ("none"/"primary"/"secondary"/"graduate")
- family_members (integer)
- children_count (integer)

IMPORTANT: The user may write in Hindi, Tamil, Telugu, or other Indian languages transliterated in English. Understand the meaning regardless of language.

Respond ONLY with valid JSON, no other text:
{"intent": "...", "profile_updates": {...}, "language_detected": "..."}"""

    response = invoke_claude(system_prompt, user_message, conversation_history)

    # Parse JSON from response
    try:
        # Handle cases where Claude wraps JSON in backticks
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        return {
            "intent": "greeting",
            "profile_updates": {},
            "language_detected": "hi"
        }


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

    return invoke_claude(full_prompt, user_message, conversation_history)
