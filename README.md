# SkillFlow

### AI-Powered Voice-First Livelihood Mapping & Skilling Pathway System

> **"From what you know to where you can go."**

SkillFlow is an AI-powered voice-first livelihood mapping and skilling pathway system. It conducts an adaptive conversational interview—in voice or text—to understand an individual's background, translates the conversation into a structured livelihood profile, and maps it against a curated, government-aligned National Skills Qualifications Framework (NSQF) knowledge base to produce explainable skilling and livelihood recommendations.

Developed for **SIH26097 — AI-Driven Voice Assistant for Livelihood Mapping and NSQF-Aligned Skilling Recommendations for SC Communities under the GIA component of PM-AJAY (Pradhan Mantri Anusuchit Jaati Abhyuday Yojana)**.

---

## 📌 Problem

Millions of informal workers, rural and semi-urban youth, and traditional artisans possess valuable practical skills but face severe barriers to formal career advancement:

1. **Digital & Literacy Barriers**: Traditional career portals and skilling portals rely on complex text-heavy forms, drop-downs, and formal resumes that intimidate and exclude non-digitally-literate workers.
2. **Invisible Skills**: Informal work experience (e.g., home tailoring, informal repair work, local agriculture, traditional weaving) is rarely documented or translated into formal qualifications.
3. **Lack of Awareness of Government Skilling**: Beneficiaries are often unaware of accredited government training programs, Qualification Packs (QPs), or NSQF pathways established under initiatives like PM-AJAY and PMKVY.
4. **Generic & Irrelevant Recommendations**: Traditional tools either recommend generic jobs without skilling pathways or force irrelevant options when no direct match exists.

---

## 💡 Solution

SkillFlow replaces static forms with an empathetic, conversational, voice-first assistant that maps informal skills to structured, accredited vocational roadmaps:

```text
🎙️ Voice / Text Input (Hindi / English)
   │
   ▼
🗣️ Speech-to-Text (Web Speech API)
   │
   ▼
🤖 Adaptive AI Interview (Gemini-Powered Turn-by-Turn Questioning)
   │
   ▼
📋 Structured Livelihood Profile Extraction (10 Dimensions)
   │
   ▼
📚 Curated NSQF Knowledge Base (23 Accredited Roles Across 7 Sectors)
   │
   ▼
⚖️ Deterministic Profile-to-Role Matching Engine
   │
   ▼
🎯 Explainable Pathway Recommendations (Up to 3 Roles, Primary & Alternative)
   │
   ▼
🔍 Skill-Gap Identification (Skills Possessed vs. Skills to Develop)
   │
   ▼
🛣️ Accredited Training & Certification Roadmap (QP Code, NSQF Level, Duration, SSC)
```

The system acts as a trusted bridge between informal, everyday experience and accredited national skilling frameworks.

---

## 🌟 Core Features

- **Voice + Text Interaction**: Natural voice input via browser-native speech recognition with simultaneous real-time text input fallback.
- **Bilingual Conversational Support**: Seamless switching between Hindi (`हिन्दी`) and English (`en-IN` / `hi-IN` recognition and speech synthesis).
- **Adaptive AI Interview**: Context-aware interview engine that asks targeted, one-at-a-time questions based on what has already been shared, eliminating repetitive questions.
- **Structured Profile Extraction**: Automatically parses natural vernacular dialogue into a normalized 10-dimension livelihood profile:
  - Highest Education
  - Current Occupation
  - Current Practical Activity
  - Years of Experience
  - Skills Possessed
  - Interests & Aspirations
  - Preferred Specialization
  - Employment Preference (Self-employment, Wage-employment, Either)
  - Mobility & Work Setting Constraints
  - Location
- **Curated NSQF-Aligned Knowledge Base**: 23 verified vocational roles across 7 sectors grounded in official Qualification Packs (QPs) from Sector Skill Councils (SSCs) and the National Qualification Register (NQR).
- **Holistic Profile-to-Role Matching**: Multi-dimensional evaluation combining practical skills, ongoing activity, experience duration, interests, preferred specializations, and work setting constraints.
- **Primary & Alternative Pathways**: Distinguishes direct interest-aligned **Primary Pathways** from skill-grounded **Skill-Based Alternative Pathways** when an exact specialization is outside the current knowledge base.
- **Explainable Recommendations**: Transparent, factual explanations detailing *why* each pathway was recommended based strictly on reported candidate profile facts.
- **Skill-Gap Analysis**: Clear side-by-side demarcation of skills the candidate already possesses versus actionable skills to develop through training.
- **Accredited Training & Certification Roadmap**: Official Qualification Pack (QP) code, NSQF level, awarding Sector Skill Council, duration, and direct links to official curriculum sources.
- **No-Padding & No-Forced Recommendations**: Returns at most 3 genuinely relevant pathways; never pads low-scoring irrelevant roles just to fill a top-3 quota.
- **Graceful No-Match Handling**: Surfaces an honest, helpful no-match state when the knowledge base lacks a sufficiently relevant role, preventing fabricated or misleading guidance.

---

## 🏗️ Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                              │
│                                                                        │
│   ┌────────────────────────┐              ┌────────────────────────┐   │
│   │   Voice / Microphone   │              │     Audio Speaker      │   │
│   │   (SpeechRecognition)  │              │   (SpeechSynthesis)    │   │
│   └───────────┬────────────┘              └───────────▲────────────┘   │
│               │ (Transcript)                          │ (Speech)       │
│               ▼                                       │                │
│   ┌───────────────────────────────────────────────────┴────────────┐   │
│   │                     SkillFlow Web UI (React 19)                │   │
│   │  • Bilingual Toggle (EN / HI)   • Visual Profile Progress Bar  │   │
│   │  • Conversational Dialogue      • Recommendations Dashboard    │   │
│   └───────────────────────────────────┬────────────────────────────┘   │
└───────────────────────────────────────┼────────────────────────────────┘
                                        │ HTTP REST (/api/*)
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND (Python)                       │
│                                                                        │
│  ┌───────────────────────┐                 ┌────────────────────────┐  │
│  │  POST /api/conversation│                │ POST /api/recommendations│
│  └───────────┬───────────┘                 └───────────┬────────────┘  │
│              │                                         │               │
│              ▼                                         ▼               │
│  ┌───────────────────────┐                 ┌────────────────────────┐  │
│  │ Gemini Conversation   │                 │ Deterministic Matching │  │
│  │        Engine         │                 │         Engine         │  │
│  │ • Adaptive Questioning│                 │ • Multi-factor Scoring │  │
│  │ • Profile Extraction  │                 │ • Skill-Gap Analysis   │  │
│  │ • Session Management  │                 │ • Pathway Structuring  │  │
│  └───────────┬───────────┘                 └───────────▲────────────┘  │
│              │                                         │               │
│              ▼                                         │               │
│  ┌───────────────────────┐                 ┌───────────┴────────────┐  │
│  │ Google Gemini 2.5     │                 │ Curated NSQF           │  │
│  │ Flash (google-genai)  │                 │ Knowledge Base         │  │
│  └───────────────────────┘                 │ (data/nsqf_roles.json) │  │
│                                            └────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: [React 19](https://react.dev/) (`react`, `react-dom`)
- **Build Tool**: [Vite 6](https://vite.dev/) (`vite`, `@vitejs/plugin-react`)
- **Styling**: Vanilla Modern CSS Design System (Custom properties, responsive Flexbox/Grid, accessible focus states, smooth transitions)
- **Typography**: Google Fonts ([Plus Jakarta Sans](https://fonts.google.com/specimen/Plus+Jakarta+Sans) for English & Latin numerals, [Noto Sans Devanagari](https://fonts.google.com/specimen/Noto+Sans+Devanagari) for Hindi)
- **Voice Engine**: Browser-native [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API) (`webkitSpeechRecognition` / `SpeechRecognition` & `window.speechSynthesis`)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (v0.111+) & [Starlette](https://www.starlette.io/)
- **Server**: [Uvicorn](https://www.uvicorn.org/) (ASGI server)
- **Data Validation & Modeling**: [Pydantic v2](https://docs.pydantic.dev/) (v2.7+)
- **Configuration**: `python-dotenv` for environment management
- **Platform**: Python 3.10+ (tested on Python 3.12 and 3.13)

### AI & Conversation Services
- **LLM Engine**: [Google Gemini 2.5 Flash](https://ai.google.dev/) via the official `google-genai` SDK
- **Prompt Strategy**: Few-shot contextual prompt guiding turn-by-turn conversational questioning and incremental profile extraction

### Data & Matching
- **Knowledge Base**: Curated JSON repository (`data/nsqf_roles.json`) verified against official Sector Skill Council Qualification Packs
- **Matching Service**: Deterministic, multi-dimensional keyword and relevance scoring engine (`backend/app/services/matching.py` and `backend/app/services/recommendations.py`)

### Quality Assurance & Validation
- **Backend Testing**: `pytest` test suite with 77 passing unit and integration tests
- **Dataset Validation**: Standalone schema and integrity validator (`tests/validate_nsqf.py`)

---

## 📚 Knowledge Base

The current MVP utilizes a **curated, government-aligned knowledge base** containing **23 verified vocational roles across 7 economic sectors**:

| Sector | Roles Count | Example Roles Included |
|---|---|---|
| **Apparel & Textiles** | 4 | Sewing Machine Operator (`AMH/Q0301`), Self-Employed Tailor (`AMH/Q1947`), Inline Checker (`AMH/Q0102`), Two Shaft Handloom Weaver (`TSC/Q7303`) |
| **Agriculture & Allied Activities** | 3 | Paddy Cultivator (`AGR/Q0101`), Organic Grower (`AGR/Q1201`), Pulses Cultivator (`AGR/Q0102`) |
| **Carpentry, Construction & Skilled Trades** | 4 | Assistant Carpenter (`FFS/Q0102`), Carpenter (`FFS/Q0103`), Assistant Shuttering Carpenter (`CON/Q0302`), Plumber - General (`PSC/Q0104`) |
| **Retail & Handicrafts** | 3 | Retail Sales Assistant (`RAS/Q0104`), Carpet Weaver (`HCS/Q5401`), Jute Handloom Weaver (`HCS/Q7401`) |
| **Digital & Entrepreneurship** | 6 | Domestic Data Entry Operator (`SSC/Q2212`), Social Media Executive (`MES/Q0702`), Social Media Manager (`MES/Q0706`), Web Developer (`SSC/Q0503`), Software Developer (`SSC/Q0501`), Database Administrator (`SSC/Q0502`) |
| **Beauty & Wellness** | 2 | Assistant Beauty Therapist (`BWS/Q0101`), Hair Dresser and Stylist (`BWS/Q0202`) |
| **Food Processing** | 1 | Food Products Packaging Technician (`FIC/Q7001`) |

### Source Attribution
Every role entry is derived strictly from public Qualification Pack (QP) documents published by official Sector Skill Councils (SSCs) and registered on the **National Qualification Register (NQR)** (`nqr.gov.in`).

### Dataset Purpose & Limitations
- **Purpose**: The dataset serves as a curated, high-integrity demonstration knowledge base to validate deterministic profile matching, explainable gap analysis, and skilling pathway recommendations.
- **Boundaries**: It is **not** a live national database, nor does it connect dynamically to real-time government registries. NSQF levels (ranging from 2.5 to 5.0) and course durations reflect the latest publicly available SSC Qualification Pack standards.

For full dataset schema and verification details, see [docs/dataset.md](file:///c:/Users/Zainab%20Shaikh/OneDrive/Documents/GitHub/SkillFlow/docs/dataset.md).

---

## ⚖️ Matching Approach

SkillFlow avoids ungrounded generative predictions ("What job should this user do?") in favor of a **deterministic profile-to-role matching process**:

1. **Holistic Profile Evaluation**: Evaluates all collected profile facets simultaneously:
   - Current occupation and practical ongoing activity
   - Years of verified/reported experience
   - Specific normalized skills possessed
   - Expressed domain interests and career goals
   - Preferred specialization (e.g., frontend development vs. backend development)
   - Preferred employment type (Self-employment vs. Wage-employment)
   - Education and entry-level eligibility requirements
   - Mobility and physical/work setting constraints (e.g., home-based tailoring)
2. **Relevance Scoring & Thresholding**:
   - Scores candidate roles based on weighted skill overlap, occupation alignment, interest concordance, and employment type preference.
   - Enforces a minimum relevance threshold (minimum score of `0.20` or direct positive signal). Roles that fail this threshold are filtered out.
3. **Primary vs. Alternative Pathway Categorization**:
   - **Primary Pathways**: Roles that directly align with the candidate's declared interest or preferred specialization.
   - **Skill-Based Alternative Pathways**: When a candidate has practical transferable skills in an adjacent domain, the system surfaces suitable roles clearly labeled as alternatives.
4. **Strict Cap of Top 3 Recommendations**:
   - Returns up to 3 highest-ranking relevant roles.
   - If only 1 or 2 roles meet the threshold, only 1 or 2 are returned. The system **never** pads irrelevant roles to reach 3.
5. **No-Match Safety**:
   - If no role meets the relevance threshold, the system returns an empty list, allowing the UI to present a helpful no-match state.

---

## 🛡️ Responsible & Trustworthy Behavior

SkillFlow is intentionally designed with strict safeguards:

- **No Fabricated Recommendations**: Pathway recommendations are produced strictly from verified records in the curated knowledge base—never hallucinated by generative models.
- **No Employment Guarantees**: SkillFlow is an educational livelihood mapping and skilling advisory system; it does not promise jobs, wage guarantees, or government placement.
- **User-Reported Skill Recognition**: Skills are recorded as reported by the candidate during the interview, not verified as formal certifications.
- **Grounded Explainability**: Every recommended pathway includes an explanation grounded directly in the user's declared profile facts and the matched Qualification Pack data.
- **Transparent Limitations**: The application transparently informs users that the current prototype operates over a curated sample of NSQF qualifications rather than an exhaustive national database.

---

## 📁 Project Structure

```text
SkillFlow/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── conversation.py        # Conversation request/response & session schemas
│   │   │   ├── profile.py             # UserProfile 10-dimension Pydantic model
│   │   │   ├── recommendation.py      # Pathway & Recommendation response schemas
│   │   │   └── role.py                # LivelihoodRole Pydantic schema
│   │   ├── routes/
│   │   │   ├── conversation.py        # POST /api/conversation (AI interview turn)
│   │   │   ├── knowledge.py           # GET /api/knowledge/* & POST /api/match
│   │   │   └── recommendations.py    # POST /api/recommendations (Top 3 pathways)
│   │   ├── services/
│   │   │   ├── conversation.py        # Gemini conversational interview engine
│   │   │   ├── knowledge_base.py      # Knowledge base loader & indexer
│   │   │   ├── matching.py            # Deterministic multi-dimensional matching
│   │   │   └── recommendations.py    # Recommendation builder & explainability
│   │   └── main.py                    # FastAPI application & CORS configuration
│   ├── tests/
│   │   ├── test_api.py                # Knowledge base & match endpoint tests
│   │   ├── test_conversation.py       # Conversational engine & session tests
│   │   ├── test_recommendations.py    # Recommendation & pathway generation tests
│   │   └── test_software_profile_regression.py # Regression & alternative pathway tests
│   ├── .env.example                   # Environment variable template
│   ├── requirements.txt               # Backend Python dependencies
│   └── README.md                      # Backend technical reference
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatDialogue.jsx       # Conversational turn display
│   │   │   ├── Header.jsx             # Top bar & bilingual toggle
│   │   │   ├── ProfileProgress.jsx    # Visual 10-dimension progress indicator
│   │   │   ├── VoiceInput.jsx         # Speech recognition & mic controls
│   │   │   └── VoiceToggle.jsx        # Speech synthesis mute/unmute control
│   │   ├── hooks/
│   │   │   └── useVoiceRecognition.js # Web Speech API recognition hook
│   │   ├── pages/
│   │   │   ├── InterviewPage.jsx      # Voice-first interview interaction view
│   │   │   └── ResultsPage.jsx        # Top 3 pathways, skill gaps & roadmaps
│   │   ├── services/
│   │   │   ├── api.js                 # Backend API client integration
│   │   │   └── voice.js               # Web Speech synthesis helper
│   │   ├── App.jsx                    # State coordinator & session manager
│   │   ├── index.css                  # Custom CSS design system & typography
│   │   └── main.jsx                   # Application entry point
│   ├── package.json                   # Frontend dependencies (React 19, Vite 6)
│   ├── vite.config.js                 # Vite dev server configuration & API proxy
│   └── README.md                      # Frontend technical reference
│
├── data/
│   └── nsqf_roles.json                # 23 curated NSQF qualification pack records
│
├── docs/
│   └── dataset.md                     # Knowledge base methodology & schema reference
│
├── tests/
│   └── validate_nsqf.py               # Standalone dataset schema & integrity validator
│
├── .gitignore
└── README.md                          # Repository documentation
```

---

## ⚡ Setup & Running Locally

### Prerequisites
- **Python**: v3.10 or higher
- **Node.js**: v18.0.0 or higher (v20+ recommended)
- **Google Gemini API Key**: Obtain a key from [Google AI Studio](https://aistudio.google.com/app/apikey)

---

### 1. Backend Setup

From the repository root:

```bash
# Navigate to the backend directory
cd backend

# Create a Python virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Copy the example file and add your Gemini API key
cp .env.example .env
```

Edit `backend/.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

Start the backend development server:
```bash
uvicorn app.main:app --reload
```
- **Backend API URL**: `http://localhost:8000`
- **Swagger Interactive Docs**: `http://localhost:8000/docs`

---

### 2. Frontend Setup

From a separate terminal in the repository root:

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```
- **Frontend Application URL**: `http://localhost:5173`

*(Vite proxies API calls to `/api` directly to `http://localhost:8000`)*

---

### 3. Production Build

To test and verify the frontend production bundle:

```bash
cd frontend
npm run build
```
Production assets are generated in `frontend/dist/`.

---

## 🔌 API Overview

SkillFlow exposes clean, RESTful endpoints documented via Swagger UI at `/docs`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check returning service status. |
| `GET` | `/api/knowledge/roles` | Lists all 23 NSQF vocational roles in the curated knowledge base. |
| `GET` | `/api/knowledge/roles/{role_id}` | Retrieves a single qualification by ID (e.g., `T-001`). |
| `GET` | `/api/knowledge/sectors` | Lists all 7 sectors and their respective role counts. |
| `POST` | `/api/match` | Accepts a `UserProfile` and returns scored candidate roles. |
| `POST` | `/api/conversation` | Processes a single conversational interview turn with Gemini LLM, returning the assistant's next question and updated profile state. |
| `POST` | `/api/recommendations` | Accepts a completed `UserProfile` and generates at most 3 explainable NSQF pathways with skill gaps and training roadmaps. |

---

## 🧪 Testing & Validation

The SkillFlow repository includes automated test coverage spanning unit, integration, and dataset validation:

### Running Backend Tests
From the `backend/` directory (with `.venv` activated):

```bash
python -m pytest
```

**Current Test Status**:
- **77 tests collected, 77 passed** (100% pass rate in ~3.8 seconds).
- Covered suites:
  - `tests/test_api.py` (21 tests) — Health, knowledge base retrieval, and deterministic matching endpoints.
  - `tests/test_conversation.py` (25 tests) — Session management, Hindi/English turns, profile extraction, and error handling.
  - `tests/test_recommendations.py` (14 tests) — Top 3 recommendation formatting, grounded explanations, and training pathway models.
  - `tests/test_software_profile_regression.py` (17 tests) — Multi-turn dialogue, software developer profiles, and skill-based alternative pathway regression.

### Running Knowledge Base Integrity Validation
From the repository root:

```bash
python tests/validate_nsqf.py
```
**Current Dataset Status**:
- **Validation Passed**: All 23 records validated with 0 schema violations, 0 empty fields, and 100% unique QP identifiers.

---

## 🎯 MVP Scope vs. Future Scope

### Implemented in Current MVP (Hackathon Ready)
- ✅ Voice-first and text-fallback conversational interview.
- ✅ Bilingual dialogue handling (Hindi and English).
- ✅ Dynamic 10-dimension structured livelihood profile extraction.
- ✅ Curated NSQF knowledge base of 23 roles across 7 sectors.
- ✅ Deterministic matching engine with relevance thresholding.
- ✅ Up to 3 explainable recommendations (Primary & Skill-Based Alternative).
- ✅ Side-by-side skill-gap analysis (skills possessed vs. skills to develop).
- ✅ Official training pathways with Qualification Pack codes and awarding bodies.
- ✅ Strict anti-padding and honest no-match handling.
- ✅ Responsive modern UI with progress tracking and mute controls.

### Future Scope (Post-MVP Roadmap)
- 🌐 **Expanded Language Coverage**: Native integration of regional Indian languages (Marathi, Tamil, Telugu, Bengali, Kannada, etc.).
- 🎙️ **Telephony & Low-Bandwidth Channels**: IVR phone line access and WhatsApp voice note interface for users without smartphones.
- 🏛️ **Live Government Portal Integrations**: Direct API linkage with Skill India Digital (SID), PM-AJAY beneficiary databases, and PMKVY training center directories.
- 🗺️ **Hyper-Local Livelihood Mapping**: District-level skill demand mapping matching candidates to local training centers.
- 📚 **Comprehensive National Knowledge Base**: Ingesting the complete 4,000+ Qualification Pack registry from the National Qualification Register (NQR).
- 📶 **Offline / Edge Deployment**: On-device lightweight models for remote areas with low or intermittent internet connectivity.

---

## 🏆 Smart India Hackathon (SIH 2026)

- **Problem ID**: SIH26097
- **Title**: AI-Driven Voice Assistant for Livelihood Mapping and NSQF-Aligned Skilling Recommendations for SC Communities under the GIA component of PM-AJAY
- **Category**: Software
- **Theme**: Smart Education / Skilling & Livelihoods
