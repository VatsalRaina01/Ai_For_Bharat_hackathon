# LokSarthi (लोकसारथी) — AI-Powered Citizen Services Platform

> **"Charioteer of the People"** — Voice-first, multilingual AI platform empowering India's underprivileged citizens to access government schemes, file RTI applications, and get financial literacy — all in their own language.

![Status](https://img.shields.io/badge/Status-Prototype-orange)
![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900)
![Languages](https://img.shields.io/badge/Languages-10+-138808)

---

## 🎯 Problem Statement

**350 million+ Indians** are eligible for government schemes but never receive benefits due to:
- 📵 **Language barrier** — Portals are in English/Hindi only
- 📖 **Literacy gap** — 25% adults can't read application forms
- 🤷 **Awareness gap** — Citizens don't know what schemes exist for them
- 📝 **RTI complexity** — Filing complaints requires legal formatting knowledge
- 💸 **Financial exploitation** — Predatory lenders charge 60-120% interest to those unaware of government alternatives

## 💡 Solution: LokSarthi

An AI voice assistant that understands citizens in **10+ Indian languages**, asks simple questions about their life, and:

1. 🏛️ **Discovers Schemes** — Matches citizen profiles against 40+ government schemes and explains benefits in plain language
2. 📝 **Drafts RTI Applications** — Converts spoken complaints into formal legal RTI applications
3. 💰 **Protects Finances** — Calculates loan EMIs, flags predatory rates, detects scams, and suggests government loan alternatives

## 🏗️ Architecture

```
Frontend (S3)  →  API Gateway  →  Lambda (FastAPI)  →  Bedrock (Claude 3 Haiku)
                                        ↕                      ↕
                                   DynamoDB              AWS Translate/Polly
                                  (Sessions)             (Multilingual)
```

**Key Services:**
- **Amazon Bedrock** (Claude 3 Haiku) — Intent detection, scheme explanations, RTI drafting
- **Amazon Translate** — Real-time translation across 10 Indian languages
- **Amazon Polly** — Text-to-speech for voice responses
- **Amazon DynamoDB** — User sessions with TTL auto-cleanup
- **AWS Lambda + API Gateway** — Serverless compute
- **Amazon S3 + CloudFront** — Frontend hosting

## 📁 Project Structure

```
├── app/
│   ├── main.py                  # FastAPI + Lambda handler
│   ├── config.py                # Environment configuration
│   ├── orchestrator.py          # Central AI brain (intent → routing)
│   ├── services/
│   │   ├── scheme_matcher.py    # 40+ scheme eligibility engine
│   │   ├── rti_assistant.py     # RTI application generator
│   │   └── financial_advisor.py # Loan calc + fraud detection
│   ├── integrations/
│   │   ├── bedrock_client.py    # Claude 3 Haiku via Bedrock
│   │   ├── language_client.py   # AWS Translate + Polly
│   │   └── dynamo_client.py     # DynamoDB sessions
│   ├── models/
│   │   └── schemas.py           # CitizenProfile, Session models
│   └── data/
│       └── schemes/
│           └── central_schemes.json  # 40 curated schemes
├── frontend/
│   ├── index.html               # Voice-first web UI
│   ├── css/styles.css           # India tricolor dark theme
│   └── js/
│       ├── app.js               # Main app logic
│       ├── api.js               # API client
│       ├── chat.js              # Chat UI
│       └── voice.js             # Web Audio recording
├── template.yaml                # AWS SAM template
├── samconfig.toml               # SAM deployment config
├── requirements.txt             # Python dependencies
├── requirements.md              # Project requirements doc
└── design.md                    # System design doc
```

## 🚀 Deployment

### Prerequisites
- AWS CLI configured with credentials
- AWS SAM CLI installed
- Python 3.12+
- Amazon Bedrock Claude 3 Haiku model access enabled

### Deploy Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Build and deploy
sam build
sam deploy --guided
```

### Deploy Frontend
```bash
# Get the frontend bucket name from SAM outputs
aws s3 sync frontend/ s3://<frontend-bucket-name>/ --delete
```

### Local Development
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Open frontend/index.html in browser
```

## 🔐 Security & Privacy

- ✅ **No PII stored** — No Aadhaar, bank details, or biometrics
- ✅ **Auto-expiry** — Sessions auto-delete via DynamoDB TTL (30 days)
- ✅ **Encryption** — AES-256 at rest, TLS 1.3 in transit
- ✅ **DPDP Act** — Right to erasure via DELETE /api/session/{id}
- ✅ **Rate limiting** — API Gateway throttling

## 💰 Cost Estimation ($100 Budget)

| Service | Monthly Cost |
|---------|-------------|
| Bedrock Claude 3 Haiku | ~$20-30 |
| Lambda + API Gateway | ~$3 |
| DynamoDB + S3 | ~$2 |
| Translate + Polly | ~$5-10 |
| **Total** | **~$35-45** |

## 🇮🇳 Supported Languages

Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi

---

*Built with ❤️ for India's citizens | AWS AI for Bharat Hackathon 2026*
