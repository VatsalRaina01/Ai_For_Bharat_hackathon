# LokSarthi (लोकसारथी) — AI Voice Assistant for Citizen Services

> **"Charioteer of the People"** — A voice-first AI assistant helping India's underserved citizens discover government schemes, file RTI applications, and get financial advice — in Hindi and English, using just their voice.

![Status](https://img.shields.io/badge/Status-Working_Prototype-brightgreen)
![AWS](https://img.shields.io/badge/AWS-Bedrock_+_Polly-FF9900)
![Languages](https://img.shields.io/badge/Voice-Hindi_+_English-138808)
![Voice](https://img.shields.io/badge/Interface-Voice_First-blue)

---

## 🎯 Problem Statement

**350 million+ Indians** are eligible for government schemes but never receive them due to:

| Barrier | Impact |
|---------|--------|
| 📵 **Language** | Government portals are English/Hindi only; 50%+ citizens speak other languages |
| 📖 **Literacy** | 25% adults can't read forms — voice is their only interface |
| 🤷 **Awareness** | Citizens don't know which of 700+ schemes they qualify for |
| 📝 **RTI complexity** | Filing complaints needs legal formatting knowledge |
| 💸 **Financial exploitation** | Predatory lenders charge 60-120% interest to the unaware |

## 💡 Solution: LokSarthi

A **voice-first AI assistant** that citizens can talk to naturally in **Hindi and English**. No reading required, no forms to fill. Extensible to more Indian languages via Amazon Polly + Translate.

### Three Service Pillars

| Pillar | What It Does | Example |
|--------|-------------|---------|
| 🏛️ **Scheme Discovery** | Asks about the citizen's life, matches against 40+ schemes | "मैं किसान हूं, बिहार से" → Finds PM-KISAN, KCC, Fasal Bima |
| 📝 **RTI / Complaint** | Converts spoken complaints into formal RTI applications | "बिजली नहीं आती" → Generates RTI for electricity department |
| 💰 **Financial Advice** | Calculates EMIs, detects scams, suggests government alternatives | "₹50,000 loan at 5% per month" → Flags predatory rate |

## 🏗️ Architecture & AWS Services

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Browser    │────▸│   FastAPI     │────▸│  Amazon Bedrock      │
│  Voice UI    │     │   Backend     │     │  (Nova Lite v1)      │
│              │◂────│              │◂────│  AI Reasoning        │
│ Web Speech   │     │ Orchestrator  │     └──────────────────────┘
│ API (STT)    │     │              │
│              │     │              │────▸┌──────────────────────┐
│ Browser TTS  │     │ Profile       │     │  Amazon Polly        │
│ + Polly HD   │◂────│ Extractor    │     │  Hindi TTS (Aditi)   │
└──────────────┘     │              │     └──────────────────────┘
                     │ Scheme        │
                     │ Matcher       │────▸  40+ Schemes JSON DB
                     └──────────────┘
```

### AWS Services Used

| Service | Purpose | Cost |
|---------|---------|------|
| **Amazon Bedrock** (Nova Lite v1) | AI brain — intent detection, profile extraction, natural conversation, scheme explanation | ~₹0.05/conversation |
| **Amazon Polly** (Aditi voice) | Hindi & English text-to-speech (hi-IN, en-IN) | ~₹0.003/response |
| **AWS STS** | Credential verification | Free |

### Browser-Based (Free, No AWS Cost)
- **Web Speech API** — Speech-to-text (STT) in the browser
- **Web Speech Synthesis** — Fallback TTS when Polly is unavailable

## ✨ Key Features

### Voice-First Conversation
- **Continuous voice mode** — Tap mic once, have a full conversation
- **Auto-send after 2.5s silence** — No buttons needed during conversation
- **Auto-listen after response** — Mic restarts when AI finishes speaking
- **Animated voice ring** — Visual feedback (🟠 listening → 🔵 thinking → 🟢 speaking)

### Smart Profile Extraction
- AI + regex fallback extracts age, gender, state, occupation from natural speech
- "मैं 25 साल की महिला किसान हूं, बिहार से" → Extracts all 4 fields in one sentence
- Progressive profiling — asks ONE question at a time, conversationally

### Scheme Matching Engine
- 40+ curated central and state government schemes
- Hard eligibility filters (age, gender, state, income, category)
- Relevance scoring for personalized ranking
- AI explains matched schemes in Hindi with ₹ amounts and how to apply

## 📁 Project Structure

```
├── app/
│   ├── main.py                  # FastAPI server + static file serving
│   ├── config.py                # Environment configuration
│   ├── orchestrator.py          # AI agent — continuous conversation brain
│   ├── services/
│   │   ├── scheme_matcher.py    # 40+ scheme eligibility engine
│   │   ├── rti_assistant.py     # RTI application generator
│   │   └── financial_advisor.py # Loan calc + fraud detection
│   ├── integrations/
│   │   ├── bedrock_client.py    # Amazon Bedrock (Nova Lite)
│   │   ├── language_client.py   # AWS Polly TTS
│   │   └── dynamo_client.py     # DynamoDB sessions
│   ├── models/
│   │   └── schemas.py           # CitizenProfile, Session models
│   └── data/schemes/
│       └── central_schemes.json # 40 curated government schemes
├── frontend/
│   ├── index.html               # Voice-first web UI
│   ├── css/styles.css           # India tricolor dark theme
│   └── js/
│       ├── app.js               # Main app logic
│       ├── api.js               # API client
│       ├── chat.js              # Voice ring states + TTS
│       └── voice.js             # Continuous voice mode
├── requirements.txt             # Python dependencies
├── run_local.py                 # Local development server
└── template.yaml                # AWS SAM template (for Lambda deploy)
```

## 🚀 Quick Start (Local)

```bash
# 1. Clone Repository
git clone https://github.com/VatsalRaina01/aws_hackathon.git
cd aws_hackathon

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Configure AWS Credentials
#    Create .env file with:
#    AWS_ACCESS_KEY_ID=your_key
#    AWS_SECRET_ACCESS_KEY=your_secret
#    AWS_REGION=us-east-1
#    BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
#    ENABLE_TTS=true

# 4. Run Server
python run_local.py

# 5. Open in Chrome/Edge
#    http://localhost:8000
#    Click the 🎤 mic button → Allow microphone → Start talking!
```

## 🔐 Security & Privacy

- ✅ **No PII stored** — No Aadhaar, bank details, or biometrics collected
- ✅ **Session auto-expiry** — DynamoDB TTL auto-deletes after 30 days
- ✅ **Encryption** — AES-256 at rest, TLS 1.3 in transit
- ✅ **DPDP Act compliant** — Right to erasure via session delete

## 💰 Cost Analysis

| Metric | Value |
|--------|-------|
| Per conversation (10 turns) | ~₹0.08 |
| Per day (1000 users) | ~₹80 |
| Per month (30K users) | ~₹2,400 (~$28) |
| **Annual (30K active users)** | **~₹29,000 (~$340)** |

Extremely affordable for government deployment at scale.

## 🇮🇳 Supported Languages

Hindi, English (full voice support) — extensible to Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi via Amazon Polly + Translate

## 🛣️ Future Roadmap

- [ ] Tamil, Telugu, Bengali voice support via Amazon Polly
- [ ] WhatsApp integration via Meta Business API
- [ ] Aadhaar-based verification for direct benefit tracking
- [ ] Offline mode using on-device models
- [ ] District-level scheme database with real-time updates
- [ ] Integration with UMANG, DigiLocker, and mySarkaar

---

*Built with ❤️ for India's citizens | AWS AI for Bharat Hackathon 2026*
