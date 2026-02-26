"""RTI Assistant — Generates RTI applications from plain-language complaints."""
import json
from app.integrations.bedrock_client import generate_response
from app.models.schemas import CitizenProfile


# RTI templates for common issues
RTI_TEMPLATES = {
    "ration_card_delay": {
        "department": "Food & Civil Supplies Department",
        "pio": "District Food & Civil Supplies Officer (DFSO)",
        "fee": "₹10",
        "questions": [
            "When was the application submitted and what is the application/reference number?",
            "What is the current status and reason for delay beyond the prescribed 15-day timeline?",
            "How many similar applications are pending in the applicant's district?",
            "What action has been taken against officials responsible for the delay?"
        ]
    },
    "pension_delay": {
        "department": "Social Welfare Department",
        "pio": "District Social Welfare Officer",
        "fee": "₹10",
        "questions": [
            "What is the current status of the pension application and reason for delay?",
            "On what date will the pension payments begin?",
            "How many pension applications are pending in the district?",
            "What corrective measures are being taken to clear the backlog?"
        ]
    },
    "road_repair": {
        "department": "Public Works Department (PWD)",
        "pio": "Executive Engineer, PWD Division",
        "fee": "₹10",
        "questions": [
            "What is the current condition report of the road and last maintenance date?",
            "What budget has been allocated for repair and what is the timeline?",
            "How many accidents have been reported on this road in the last 12 months?",
            "What action has been taken on previous complaints regarding this road?"
        ]
    },
    "water_supply": {
        "department": "Public Health Engineering / Jal Shakti Department",
        "pio": "Executive Engineer, PHED Division",
        "fee": "₹10",
        "questions": [
            "What is the schedule and source of water supply in the applicant's area?",
            "What is the reason for irregular/no water supply?",
            "What budget has been allocated for water infrastructure improvement?",
            "When will regular supply be restored?"
        ]
    },
    "scheme_benefit_not_received": {
        "department": "Respective scheme department",
        "pio": "District level officer of the concerned department",
        "fee": "₹10",
        "questions": [
            "What is the current status of the applicant's enrollment in the scheme?",
            "If approved, on what date was the benefit disbursed and to which account?",
            "If rejected, what is the reason for rejection and appeal process?",
            "How many beneficiaries in the district are yet to receive their benefits?"
        ]
    },
    "electricity_issue": {
        "department": "State Electricity Distribution Company (DISCOM)",
        "pio": "Superintending Engineer, DISCOM",
        "fee": "₹10",
        "questions": [
            "What is the status of the electricity connection application/complaint?",
            "What is the reason for power outages and expected resolution date?",
            "What is the average power supply hours in the applicant's area?",
            "What compensation is applicable under consumer protection norms?"
        ]
    },
    "mgnrega_wage_delay": {
        "department": "District Rural Development Agency (DRDA)",
        "pio": "District Programme Coordinator, MGNREGA",
        "fee": "₹10 (BPL applicants exempted)",
        "questions": [
            "What is the total number of days worked and wage due to the applicant?",
            "Why have wages not been paid within the statutory 15-day period?",
            "What compensation is due under delayed payment provisions of MGNREGA?",
            "How many workers in the district have pending wage payments?"
        ]
    },
    "general": {
        "department": "To be identified based on complaint",
        "pio": "Public Information Officer of the concerned department",
        "fee": "₹10 (BPL exempted)",
        "questions": [
            "Please provide complete information regarding the subject matter",
            "What actions have been taken on previous requests/complaints?",
            "What is the timeline for resolution?",
            "Who is the responsible officer?"
        ]
    }
}


def classify_complaint(complaint_text: str) -> dict:
    """Use AI to classify the complaint and extract key details."""
    system_prompt = """You are an RTI expert for India. Analyze the citizen's complaint and classify it.

Return ONLY valid JSON:
{
    "category": one of ["ration_card_delay", "pension_delay", "road_repair", "water_supply", "scheme_benefit_not_received", "electricity_issue", "mgnrega_wage_delay", "general"],
    "department": "specific government department name",
    "issue_summary": "one-line summary of the issue",
    "location": "city/district/state mentioned",
    "duration": "how long the issue has persisted",
    "previous_attempts": "any previous complaints mentioned"
}"""

    response = generate_response(system_prompt, complaint_text)
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        return {
            "category": "general",
            "department": "Concerned department",
            "issue_summary": complaint_text[:200],
            "location": "",
            "duration": "",
            "previous_attempts": ""
        }


def generate_rti_application(complaint_text: str, profile: CitizenProfile) -> str:
    """Generate a formal RTI application from a plain-language complaint."""

    # Step 1: Classify the complaint
    classification = classify_complaint(complaint_text)
    category = classification.get("category", "general")
    template = RTI_TEMPLATES.get(category, RTI_TEMPLATES["general"])

    # Step 2: Generate the formal RTI application using AI
    system_prompt = f"""You are an expert RTI application drafter for India.

COMPLAINT: {complaint_text}
CLASSIFICATION: {json.dumps(classification, ensure_ascii=False)}
TEMPLATE DEPARTMENT: {template['department']}
TEMPLATE PIO: {template['pio']}
TEMPLATE FEE: {template['fee']}
SUGGESTED QUESTIONS: {json.dumps(template['questions'], ensure_ascii=False)}

CITIZEN PROFILE:
Name: [Citizen's name - to be filled]
Address: {profile.state or '[State]'}, {profile.district or '[District]'}

Generate a COMPLETE, FORMAL RTI application in the following format:

---
**RTI APPLICATION**
Under Section 6(1) of the Right to Information Act, 2005

To,
The Public Information Officer,
[Department name],
[Address]

Subject: Application seeking information under RTI Act, 2005 regarding [issue]

Sir/Madam,

I, [Name], resident of [address], hereby seek the following information under the Right to Information Act, 2005:

[Numbered list of 4-6 specific, pointed questions about the issue]

I am enclosing the prescribed fee of {template['fee']} [payment mode].

[If BPL: I belong to Below Poverty Line category and am exempted from paying the fee as per Section 7(5) of the RTI Act, 2005. A copy of my BPL certificate is enclosed.]

I request that the information be provided within the statutory period of 30 days.

Yours faithfully,
[Name]
[Address]
[Phone]
Date: [Current Date]

Enclosures:
1. Fee payment proof / BPL certificate
2. [Any relevant document copies]
---

Make the questions SPECIFIC to the citizen's actual complaint, not generic. Include the template questions but customize them.
Respond in English (the RTI application should be in English as it's a legal document)."""

    rti_text = generate_response(system_prompt, complaint_text)

    # Add submission instructions
    instructions = f"""

📋 **HOW TO SUBMIT THIS RTI:**

1. **Online (Easiest):** Go to rtionline.gov.in → Click "Submit Request" → Select department → Paste this application → Pay ₹10 online
2. **By Post:** Print this, attach ₹10 postal order/DD, send by registered post to the PIO address
3. **In Person:** Visit the PIO office with this application and ₹10 fee

⏰ **Timeline:** You will receive a response within 30 days. If not, you can file a First Appeal.
💡 **Tip:** Keep a copy of the application and acknowledgment receipt for your records.
🆓 **BPL Citizens:** You are exempted from the ₹10 fee. Attach your BPL certificate instead.

Department: {template['department']}
PIO: {template['pio']}
"""

    return rti_text + instructions


def handle_rti_request(user_message: str, profile: CitizenProfile, language: str = "hi") -> str:
    """Main handler for RTI-related requests."""

    system_prompt = f"""You are LokSarthi's RTI Assistant. The citizen wants to file an RTI or grievance.

CITIZEN'S MESSAGE: {user_message}
CITIZEN PROFILE: {json.dumps(profile.to_dict(), ensure_ascii=False)}

Determine what the citizen needs:
1. If they have a clear complaint → Generate the RTI application
2. If the complaint is vague → Ask clarifying questions (which department? what happened? when? where?)
3. If they want to know about RTI → Explain what RTI is and how it works

Respond in the citizen's language ({language}). Be empathetic and encouraging.
If generating an RTI, also explain in simple language what you've done and next steps."""

    # Check if we have enough info to generate an RTI
    if len(user_message.split()) > 10:  # Substantial complaint
        rti_application = generate_rti_application(user_message, profile)

        # Generate a simple explanation in the user's language
        explanation_prompt = f"""Explain to the citizen in {language} language (use simple words):
1. You have created an RTI application for them
2. Their complaint is about: [summarize briefly]
3. They need to submit it to [department]
4. It will cost ₹10 (free for BPL)
5. They will get a response in 30 days
6. Ask if they want to modify anything

Keep it warm, encouraging, and simple. Use phrases like "Aapki RTI tayyar hai!" """

        explanation = generate_response(explanation_prompt, user_message)
        return explanation + "\n\n" + rti_application
    else:
        return generate_response(system_prompt, user_message)
