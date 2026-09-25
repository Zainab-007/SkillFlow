# SkillFlow

### AI-Powered Voice Assistant for Livelihood Mapping & Skill Pathways

> **From what you know to where you can go.**

SkillFlow is an AI-powered voice assistant designed to understand a person's **education, occupation, experience, skills, interests, constraints, and employment preferences** through a natural conversation.

It then builds a structured livelihood profile, identifies potential skill gaps, and recommends relevant **NSQF-aligned training and livelihood pathways** with an explainable roadmap.

Built for **SIH26097 — AI-Driven Voice Assistant for Livelihood Mapping and NSQF-Aligned Skilling Recommendations for SC Communities under the GIA component of PM-AJAY.**

---

## ✨ What SkillFlow Does

SkillFlow turns a natural conversation into an actionable skill pathway:

```text
🎙️ Speak
   ↓
🧠 AI understands your profile
   ↓
📋 Structured livelihood profile
   ↓
🔍 Skill-gap identification
   ↓
🎯 Personalized pathway recommendations
   ↓
🛣️ Training → Certification → Livelihood
```

The goal is to make skill discovery and livelihood guidance feel like a **conversation, not a form**.

---

## 🚀 MVP

The SkillFlow prototype focuses on six core capabilities:

* 🎙️ **Voice-first interaction** with text input as a fallback
* 🌐 **Hindi + English** conversational support
* 🧠 **Adaptive AI interview** that decides what to ask next
* 📋 **Structured profile extraction** from natural conversation
* 🔍 **Skill-gap analysis and pathway matching**
* 🎯 **Top 3 explainable recommendations** with a simple livelihood roadmap

### Example

A user says:

> "I've been doing tailoring from home for three years. I know sewing and alterations, but I don't know much about selling online."

SkillFlow can identify:

```text
Education        → 12th
Occupation       → Tailoring
Experience       → 3 years
Skills           → Sewing, Tailoring, Alteration
Goal             → Self-employment
Skill Gaps       → Digital Marketing, Online Selling
```

It can then match the profile against its curated knowledge base and explain **why** each pathway was recommended.

---

## 🧩 Core Architecture

```text
                  ┌─────────────────┐
                  │      User       │
                  └────────┬────────┘
                           │
                    Voice / Text
                           │
                           ▼
                  ┌─────────────────┐
                  │ Speech-to-Text  │
                  └────────┬────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  LLM Conversation       │
              │       Engine            │
              │                         │
              │ • Adaptive Questions    │
              │ • Profile Extraction    │
              └────────────┬────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Profile / State │
                  └────────┬────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   Skill-Gap Engine      │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   Matching Engine       │
              │                         │
              │ Curated Knowledge Base  │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ Top 3 Recommendations   │
              │ + Explainable "Why"     │
              └────────────┬────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Results +      │
                  │  Roadmap        │
                  └─────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend

* React
* Vite
* Tailwind CSS

### Backend

* Python
* FastAPI
* Pydantic

### AI

* LLM-based conversational engine
* Speech-to-Text
* Text-to-Speech

### Data & Matching

* Curated NSQF-aligned knowledge base
* JSON-based prototype dataset
* Python-based skill matching
* LLM-generated explanations grounded in matched records

### Development

* Git
* GitHub
* VS Code

---

## 📁 Project Structure

```text
SkillFlow/
│
├── backend/
│   └── app/
│       ├── routes/
│       ├── services/
│       ├── models/
│       └── main.py
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── App.jsx
│
├── data/
│   └── nsqf_roles.json
│
├── docs/
│
├── tests/
│
├── .gitignore
└── README.md
```

---

## 📊 Profile Fields

During the conversation, SkillFlow aims to understand:

```text
Education
Current Occupation
Experience
Skills
Interests
Mobility / Physical Constraints
Employment Preference
Location
```

The AI asks **one question at a time** and avoids repeatedly asking for information that has already been provided.

---

## 🎯 Recommendation Approach

SkillFlow does not simply ask an LLM:

> "What career should this person choose?"

Instead:

```text
User Profile
     ↓
Skill & Interest Matching
     ↓
Curated Knowledge Base
     ↓
Candidate Pathways
     ↓
Skill Gaps
     ↓
Top 3 Recommendations
     ↓
Grounded Explanation
```

The recommendation explanation is generated using the user's profile and the matched knowledge-base records to reduce unsupported claims.

---

## 📚 Knowledge Base

The prototype uses a **curated, government-aligned knowledge base** containing approximately 15–25 relevant vocational roles/pathways across multiple sectors.

Each record contains information such as:

* Role / pathway
* Sector
* NSQF level, where verified
* Required skills
* Relevant skill gaps
* Eligibility
* Duration, where available
* Description
* Source
* Verification date

> The prototype does **not** claim to provide live government or labour-market data.

---

## 🗣️ Supported Languages

### Current MVP

* 🇮🇳 Hindi
* 🇬🇧 English

Additional languages may be explored as future scope depending on Speech-to-Text and Text-to-Speech reliability.

---

## 🔮 Future Scope

The MVP intentionally keeps the system focused.

Potential future extensions include:

* IVR / phone-call access
* WhatsApp voice interaction
* Additional Indian languages and dialects
* Geographic livelihood mapping
* Live labour-market data
* Government platform/API integrations
* Offline deployment
* Mobile application
* Administrative analytics dashboard
* Larger knowledge base
* More advanced semantic/embedding-based matching

---

## ⚠️ Scope & Responsible Use

SkillFlow is a **prototype for livelihood and skilling guidance**.

Recommendations are intended to help users explore relevant pathways. They do not guarantee employment, income, certification, or eligibility for any particular government programme.

The prototype uses a curated knowledge base rather than claiming live government-data integration.

---

## 🏆 SIH 2026

**Problem Statement:** SIH26097

**Theme:** Smart Education

**Category:** Software

**Project:** SkillFlow

**Team:** [Add Team Name]

---

## 📌 Current Status

```text
🟡 Project initialization
```

### Roadmap

* [ ] Repository setup
* [ ] Research & build knowledge base
* [ ] Backend foundation
* [ ] AI conversation engine
* [ ] Profile extraction
* [ ] Skill-gap engine
* [ ] Recommendation engine
* [ ] Voice interaction
* [ ] Results dashboard
* [ ] End-to-end integration
* [ ] Testing
* [ ] Demo preparation
