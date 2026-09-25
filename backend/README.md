# SkillFlow Backend

FastAPI backend for the SkillFlow livelihood mapping and NSQF-aligned skilling assistant.

---

## Prerequisites

- Python 3.10 or later
- The repository must be cloned with `data/nsqf_roles.json` present at the **project root** level (one directory above `backend/`).

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

---

## Running the server

From the `backend/` directory (with the virtual environment activated):

```bash
uvicorn app.main:app --reload
```

The server will start at: **http://localhost:8000**

Interactive API docs: **http://localhost:8000/docs**

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/knowledge/roles` | List all 20 NSQF roles |
| GET | `/api/knowledge/roles/{role_id}` | Get a single role by ID (e.g. `T-001`) |
| GET | `/api/knowledge/sectors` | List sectors and role counts |
| POST | `/api/match` | Match a user profile to roles |

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

From the `backend/` directory (with the virtual environment activated):

```bash
pip install pytest httpx
pytest tests/ -v
```

---

## Architecture Notes

```
backend/app/
├── main.py                     # FastAPI app, CORS, router registration
├── models/
│   ├── profile.py              # UserProfile Pydantic model
│   └── role.py                 # LivelihoodRole + related Pydantic models
├── services/
│   ├── knowledge_base.py       # Loads data/nsqf_roles.json; single source of truth
│   └── matching.py             # Deterministic keyword skill-matching service
└── routes/
    └── knowledge.py            # /api/health, /api/knowledge/*, /api/match
```

### Matching algorithm (summary)

The matching service uses **deterministic normalised keyword matching** — no LLM, no embeddings.

For each role in the knowledge base, a score is computed as:

```
skill_score   = (matched required_skills) / (total required_skills)   [weight 0.6]
interest_score = interest terms found in title/sector                  [weight 0.2]
occupation_score = occupation terms found in title/required_skills     [weight 0.2]

final_score = 0.6 * skill_score + 0.2 * interest_score + 0.2 * occupation_score
```

All comparisons are lowercase and strip punctuation for robustness.

The result includes `matched_skills` (overlapping skills the user already has) and `skill_gaps` (what the training would additionally provide that the user does not yet have).

Results are sorted by `score` descending.

---

## Next steps (not yet implemented)

- STT / TTS integration
- LLM conversation engine (Gemini)
- Structured profile extraction from conversation
- Frontend (React + Vite + Tailwind)
