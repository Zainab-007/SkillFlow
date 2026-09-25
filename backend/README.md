# SkillFlow Backend

FastAPI backend for the SkillFlow AI-powered livelihood mapping and NSQF-aligned skilling assistant.

---

## Prerequisites

- Python 3.10 or later
- The repository must be cloned with `data/nsqf_roles.json` present at the **project root** level (one directory above `backend/`).
- A Google Gemini API key (for the LLM conversation engine). Get one at [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## Setup

### 1. Create a virtual environment

From the `backend/` directory:

```bash
python -m venv .venv
```

### 2. Activate the virtual environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Running the server

From the `backend/` directory (with the virtual environment activated):

```bash
uvicorn app.main:app --reload
```

The server starts at: **http://localhost:8000**

Interactive API docs: **http://localhost:8000/docs**

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/knowledge/roles` | List all 20 NSQF roles |
| GET | `/api/knowledge/roles/{role_id}` | Get a single role by ID (e.g. `T-001`) |
| GET | `/api/knowledge/sectors` | List sectors and role counts |
| POST | `/api/match` | Match a user profile to roles (deterministic) |
| POST | `/api/conversation` | Process one conversational turn with Gemini LLM |

---

### Example: Conversation request

```bash
curl -X POST http://localhost:8000/api/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "language": "en",
    "message": "Hello, I do stitching and alteration at home."
  }'
```

Response format:
```json
{
  "reply": "That is wonderful! How many years have you been doing stitching and alteration?",
  "profile": {
    "education": null,
    "current_occupation": "Stitching and alteration",
    "experience_years": null,
    "skills": ["stitching", "alteration"],
    "interests": [],
    "employment_preference": "Self-employment",
    "location": null
  },
  "is_complete": false,
  "language": "en",
  "missing_fields": ["education", "experience_years", "interests", "location"]
}
```

---

### Example: Match request

```bash
curl -X POST http://localhost:8000/api/match \
  -H "Content-Type: application/json" \
  -d '{
    "education": "12th",
    "current_occupation": "Tailoring",
    "experience_years": 3,
    "skills": ["Sewing", "Tailoring", "Alteration"],
    "interests": ["Fashion"],
    "employment_preference": "Self-employment",
    "location": "Mumbai"
  }'
```

---

## Running tests

From the root or `backend/` directory:

```bash
pytest backend/tests/ -v
```

All 43 unit and integration tests (21 knowledge/matching + 22 conversation engine) run with Gemini API calls mocked, so no live API key is required during testing.

---

## Architecture Notes

```
backend/
├── .env.example                # API key template
├── requirements.txt            # Dependencies including google-genai
├── app/
│   ├── main.py                 # FastAPI app, CORS, router registration
│   ├── models/
│   │   ├── conversation.py     # Request, Response, and LLM output schemas
│   │   ├── profile.py          # UserProfile Pydantic model
│   │   └── role.py             # LivelihoodRole + related Pydantic models
│   ├── services/
│   │   ├── conversation.py     # Gemini LLM interview engine & session store
│   │   ├── knowledge_base.py   # Loads data/nsqf_roles.json (single source of truth)
│   │   └── matching.py         # Deterministic keyword skill-matching service
│   └── routes/
│       ├── conversation.py     # POST /api/conversation
│       └── knowledge.py        # /api/health, /api/knowledge/*, /api/match
└── tests/
    ├── test_api.py             # Knowledge base & deterministic matching tests
    └── test_conversation.py    # Conversation engine mocked tests
```
