"""Scheme Matcher — Matches citizen profiles against government schemes."""
import json
import os
from typing import Optional
from app.models.schemas import CitizenProfile
from app.integrations.bedrock_client import generate_response

# Load schemes data at module level (reused across invocations)
_schemes = None


def _load_schemes() -> list:
    global _schemes
    if _schemes is None:
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "schemes", "central_schemes.json")
        with open(data_path, "r", encoding="utf-8") as f:
            _schemes = json.load(f)
    return _schemes


def _passes_filter(profile: CitizenProfile, rules: dict) -> bool:
    """Check if a citizen passes the hard eligibility filters for a scheme."""

    # Age filter
    if "age_min" in rules and profile.age is not None:
        if profile.age < rules["age_min"]:
            return False
    if "age_max" in rules and profile.age is not None:
        if profile.age > rules["age_max"]:
            return False

    # Gender filter
    if "gender" in rules and profile.gender is not None:
        if profile.gender not in rules["gender"]:
            return False

    # State filter
    if "states" in rules and profile.state is not None:
        if profile.state.lower() not in [s.lower() for s in rules["states"]]:
            return False

    # Occupation filter
    if "occupations" in rules and profile.occupation is not None:
        if profile.occupation not in rules["occupations"]:
            return False

    # Category filter
    if "categories" in rules and profile.category is not None:
        if profile.category not in rules["categories"]:
            return False

    # Income filter
    if "income_max" in rules and profile.annual_income is not None:
        if profile.annual_income > rules["income_max"]:
            return False

    # BPL filter
    if rules.get("bpl_required") and profile.bpl_status is not None:
        if not profile.bpl_status:
            return False

    # Disability filter
    if rules.get("disability_required") or rules.get("disability"):
        if profile.disability is not None and not profile.disability:
            return False

    # Land ownership filter
    if rules.get("land_required") and profile.land_ownership is not None:
        if not profile.land_ownership:
            return False

    # Marital status filter
    if "marital_status" in rules and profile.marital_status is not None:
        if profile.marital_status not in rules["marital_status"]:
            return False

    return True


def _relevance_score(profile: CitizenProfile, scheme: dict) -> float:
    """Calculate relevance score (0-100) for a scheme based on profile match."""
    score = 50  # Base score for passing filters
    rules = scheme.get("eligibility", {})

    # Bonus for specific matches
    if "occupations" in rules and profile.occupation:
        if profile.occupation in rules["occupations"]:
            score += 15

    if "categories" in rules and profile.category:
        if profile.category in rules["categories"]:
            score += 10

    if "gender" in rules and profile.gender:
        if profile.gender in rules["gender"]:
            score += 10

    if rules.get("bpl_required") and profile.bpl_status:
        score += 10

    # Bonus for high-value benefits
    benefit = scheme.get("benefit_amount", "")
    if "lakh" in benefit.lower() or "₹5,00,000" in benefit:
        score += 5

    return min(score, 100)


def match_schemes(profile: CitizenProfile, max_results: int = 7) -> list:
    """
    Match citizen profile against all schemes and return top matches.

    Returns:
        List of {scheme, score, reason} sorted by relevance
    """
    schemes = _load_schemes()
    matches = []

    for scheme in schemes:
        rules = scheme.get("eligibility", {})

        # Empty eligibility = universal scheme, everyone eligible
        if not rules or _passes_filter(profile, rules):
            score = _relevance_score(profile, scheme)
            matches.append({
                "scheme": scheme,
                "score": score,
            })

    # Sort by score descending
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:max_results]


def get_profiling_question(profile: CitizenProfile) -> Optional[str]:
    """
    Determine what question to ask next to complete the citizen profile.

    Returns:
        Question string, or None if profile is sufficiently complete
    """
    if profile.completeness_score() >= 0.8:
        return None

    # Ask questions in priority order
    if profile.age is None:
        return "age"
    if profile.gender is None:
        return "gender"
    if profile.state is None:
        return "state"
    if profile.occupation is None:
        return "occupation"
    if profile.category is None:
        return "category"
    if profile.annual_income is None:
        return "income"
    if profile.marital_status is None:
        return "marital_status"
    if profile.bpl_status is None:
        return "bpl"

    return None


def explain_schemes(matched_schemes: list, profile: CitizenProfile, language: str = "hi") -> str:
    """
    Use Bedrock to generate a friendly explanation of matched schemes.
    """
    if not matched_schemes:
        return "I couldn't find any matching schemes based on your profile. Let me ask a few more questions to improve the results."

    # Build scheme summary for context
    scheme_summaries = []
    for i, match in enumerate(matched_schemes[:5], 1):
        s = match["scheme"]
        scheme_summaries.append(
            f"{i}. {s['name']} ({s.get('name_hi', '')})\n"
            f"   Benefit: {s['benefit_amount']}\n"
            f"   Documents: {', '.join(s.get('documents', []))}\n"
            f"   How to apply: {s['how_to_apply']}"
        )

    context_data = "\n\n".join(scheme_summaries)

    system_prompt = f"""You are LokSarthi, a warm and caring AI assistant helping Indian citizens discover government schemes.

CITIZEN PROFILE:
{json.dumps(profile.to_dict(), ensure_ascii=False)}

MATCHED SCHEMES (ranked by relevance):
{context_data}

INSTRUCTIONS:
1. Explain the top matched schemes in simple, everyday language (5th-grade level)
2. For each scheme, explain: what benefit they get, why they qualify, what documents to keep ready, and where to apply
3. Use ₹ amounts and real numbers
4. Be encouraging — "Aapko yeh milega!" (You will get this!)
5. If the language is Hindi, respond in Hindi. If English, respond in English.
6. Keep it conversational, not formal
7. At the end, ask if they want more details about any specific scheme
8. Mention that you can also help with RTI applications and financial advice"""

    return generate_response(system_prompt, f"Please explain my eligible schemes. My language is: {language}")
