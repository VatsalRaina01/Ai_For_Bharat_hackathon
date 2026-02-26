"""Financial Advisor — Loan calculator, fraud detection, and financial literacy."""
import json
from app.integrations.bedrock_client import generate_response
from app.models.schemas import CitizenProfile


# Known scam patterns
SCAM_PATTERNS = [
    {
        "keywords": ["otp", "share otp", "otp batao", "otp do"],
        "alert_hi": "🚨 ख़तरा! OTP कभी किसी को मत दीजिए। कोई भी बैंक या सरकारी अधिकारी OTP नहीं मांगता। यह 100% FRAUD है।",
        "alert_en": "🚨 DANGER! Never share your OTP with anyone. No bank or government official ever asks for OTP. This is 100% FRAUD."
    },
    {
        "keywords": ["advance fee", "processing fee pehle", "pehle paisa do", "loan ke liye paisa"],
        "alert_hi": "🚨 ख़तरा! लोन लेने के लिए पहले पैसा देना FRAUD है। कोई भी सरकारी योजना या बैंक पहले पैसा नहीं मांगता।",
        "alert_en": "🚨 DANGER! Paying money upfront to get a loan is FRAUD. No government scheme or bank asks for advance payment."
    },
    {
        "keywords": ["lottery", "prize", "jackpot", "inam", "crore jeet"],
        "alert_hi": "🚨 ख़तरा! यह FRAUD है। आपने कोई लॉटरी नहीं जीती। पैसा बिल्कुल मत दीजिए।",
        "alert_en": "🚨 DANGER! This is FRAUD. You have not won any lottery. Do NOT send any money."
    },
    {
        "keywords": ["insurance expire", "kyc update", "account block", "account band"],
        "alert_hi": "🚨 सावधान! यह शायद FRAUD है। बैंक कभी फोन पर KYC update नहीं करवाता। अपने नज़दीकी बैंक ब्रांच में जाकर पूछें।",
        "alert_en": "🚨 CAUTION! This is likely FRAUD. Banks never do KYC updates over phone. Visit your nearest bank branch."
    },
    {
        "keywords": ["link click", "click karo", "link open", "form bharo online"],
        "alert_hi": "🚨 सावधान! अनजान लिंक पर क्लिक मत करें। हमेशा सरकारी वेबसाइट (.gov.in) पर ही जाएं।",
        "alert_en": "🚨 CAUTION! Do not click unknown links. Always visit official government websites (.gov.in)."
    }
]

# Government loan alternatives
GOVT_LOAN_SCHEMES = [
    {"name": "PM MUDRA Yojana", "rate": "7-9%", "amount": "Up to ₹10 lakh", "for": "Small business"},
    {"name": "PM SVANidhi", "rate": "7% subsidy", "amount": "₹10,000-₹50,000", "for": "Street vendors"},
    {"name": "KCC (Kisan Credit Card)", "rate": "4% (subsidized)", "amount": "Up to ₹3 lakh", "for": "Farmers"},
    {"name": "Stand-Up India", "rate": "Bank rate", "amount": "₹10 lakh - ₹1 crore", "for": "SC/ST/Women entrepreneurs"},
    {"name": "PMEGP", "rate": "25-35% subsidy", "amount": "Up to ₹50 lakh", "for": "New businesses"},
    {"name": "SHG Bank Linkage", "rate": "4-7%", "amount": "Up to ₹20 lakh", "for": "Women's Self Help Groups"},
]


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> dict:
    """
    Calculate EMI and total cost of a loan.

    Returns detailed breakdown in both English and Hindi-friendly format.
    """
    if annual_rate <= 0 or tenure_months <= 0 or principal <= 0:
        return {"error": "Invalid loan parameters"}

    monthly_rate = annual_rate / (12 * 100)
    emi = principal * monthly_rate * (1 + monthly_rate)**tenure_months / ((1 + monthly_rate)**tenure_months - 1)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal
    interest_percentage = (total_interest / principal) * 100

    return {
        "principal": principal,
        "annual_rate": annual_rate,
        "tenure_months": tenure_months,
        "monthly_emi": round(emi),
        "total_payment": round(total_payment),
        "total_interest": round(total_interest),
        "interest_percentage": round(interest_percentage, 1),
        "is_predatory": annual_rate > 36,
        "risk_level": "HIGH" if annual_rate > 36 else "MEDIUM" if annual_rate > 24 else "LOW",
    }


def detect_scam(text: str) -> dict:
    """Check if the described situation matches known scam patterns."""
    text_lower = text.lower()

    for pattern in SCAM_PATTERNS:
        for keyword in pattern["keywords"]:
            if keyword in text_lower:
                return {
                    "is_scam": True,
                    "alert_hi": pattern["alert_hi"],
                    "alert_en": pattern["alert_en"],
                }

    return {"is_scam": False}


def detect_predatory_lending(annual_rate: float) -> dict:
    """Flag predatory interest rates and suggest alternatives."""
    if annual_rate > 36:
        return {
            "is_predatory": True,
            "alert_hi": f"⚠️ ख़तरा: {annual_rate}% सालाना ब्याज बहुत ज़्यादा है! यह शोषणकारी (predatory) लेंडिंग है। सरकारी योजनाओं से 4-9% ब्याज पर लोन मिल सकता है।",
            "alert_en": f"⚠️ DANGER: {annual_rate}% annual interest is extremely high! This is predatory lending. Government schemes offer loans at 4-9% interest.",
            "alternatives": GOVT_LOAN_SCHEMES[:3],
        }
    elif annual_rate > 24:
        return {
            "is_predatory": False,
            "is_high": True,
            "alert_hi": f"⚠️ सावधान: {annual_rate}% ब्याज काफ़ी ज़्यादा है। सरकारी योजनाओं में कम ब्याज पर लोन उपलब्ध है।",
            "alert_en": f"⚠️ CAUTION: {annual_rate}% interest is quite high. Government schemes offer lower rates.",
            "alternatives": GOVT_LOAN_SCHEMES[:3],
        }
    else:
        return {
            "is_predatory": False,
            "is_high": False,
            "alert_en": f"✅ {annual_rate}% annual interest is within reasonable range.",
        }


def handle_financial_query(user_message: str, profile: CitizenProfile, language: str = "hi") -> str:
    """Main handler for financial queries."""

    # Check for scam patterns first
    scam_check = detect_scam(user_message)
    if scam_check["is_scam"]:
        alert = scam_check.get(f"alert_{language}", scam_check["alert_en"])
        return alert

    # Build context with government alternatives
    alternatives_text = "\n".join([
        f"- {s['name']}: {s['rate']} interest, {s['amount']} — for {s['for']}"
        for s in GOVT_LOAN_SCHEMES
    ])

    system_prompt = f"""You are LokSarthi's Financial Advisor. Help the citizen with financial literacy.

CITIZEN PROFILE: {json.dumps(profile.to_dict(), ensure_ascii=False)}
LANGUAGE: {language}

GOVERNMENT LOAN ALTERNATIVES (always mention these as better options):
{alternatives_text}

YOUR CAPABILITIES:
1. **Loan Explanation**: If they mention a loan amount/rate, calculate EMI and explain in exact ₹ amounts
2. **Fraud Detection**: Flag predatory rates (>36% annual = exploitative, >24% = high)
3. **Scam Alert**: Warn about OTP scams, advance fee frauds, fake lotteries
4. **Government Alternatives**: Always suggest cheaper government loan schemes
5. **Savings Advice**: Explain Sukanya Samriddhi, PPF, PM Jan Dhan benefits
6. **GST Basics**: Simple explanation if asked

RULES:
- Always use exact ₹ amounts, never percentages alone
- Compare sahukar/private rates with government rates
- Be protective — assume the citizen might be getting exploited
- Respond in {language} language
- Use simple, everyday words
- If they mention monthly rates (like "5% per month"), convert to annual (5% × 12 = 60% annual!) and flag it

Example: If someone says "sahukar is offering 5% monthly rate on ₹50,000 loan":
- Convert: 5% monthly = 60% annual — this is EXPLOITATIVE!
- Calculate exact EMI and total repayment
- Show how much they'd save with PM MUDRA at 8% instead
- Guide them to apply for MUDRA loan"""

    return generate_response(system_prompt, user_message)
