# SkillFlow Frontend

React + Vite frontend for SkillFlow — AI-Driven Voice Assistant for Livelihood Mapping & NSQF-Aligned Skilling Recommendations under PM-AJAY (SIH26097).

---

## Overview

This is an accessible, voice-first and text-fallback conversational interface designed to guide individuals through an empathetic livelihood interview.

Key features:
- **Bilingual Interface**: Toggle between English and Hindi (`हिंदी`).
- **Web Speech Recognition**: Browser-native speech recognition (`en-IN` and `hi-IN`).
- **SpeechSynthesis Text-to-Speech**: Automatic audible reading of assistant questions with a voice mute/unmute control.
- **Robust Fallback**: Full keyboard and text input support if microphone permission is denied or Web Speech APIs are unavailable.
- **Dynamic Profile Progress**: Visual tracking of collected livelihood dimensions with human-friendly labels.
- **Results Summary**: Clean presentation of the synthesized livelihood profile.

---

## Prerequisites

- **Node.js**: v18.0.0 or later (v20+ recommended)
- **SkillFlow Backend**: FastAPI backend running on `http://localhost:8000`

---

## Setup & Running Locally

### 1. Install Dependencies

From the `frontend/` directory:

```bash
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The frontend will be available at: **http://localhost:5173**

API requests to `/api` are automatically proxied to the backend at **http://localhost:8000**.

### 3. Build for Production

```bash
npm run build
```

Production assets will be generated in `frontend/dist/`.

---

## URLs

| Service | Local Address |
|---|---|
| Frontend Web UI | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Backend Swagger Docs | http://localhost:8000/docs |

---

## Voice & Browser Capabilities

The voice capabilities in this prototype utilize standard HTML5 / Web Speech APIs built directly into modern web browsers:

1. **Speech Recognition (`Web Speech API`)**:
   - Supported natively in Google Chrome, Microsoft Edge, and Chromium-based browsers.
   - Requires user microphone permission.
   - Configured with `en-IN` (Indian English) and `hi-IN` (Hindi) recognition models.
2. **Text-to-Speech (`SpeechSynthesis API`)**:
   - Supported across all modern desktop and mobile browsers (Chrome, Edge, Safari, Firefox).
   - Voice selection selects `en-IN` or `hi-IN` OS voices where installed, falling back cleanly to available English/general voices.

### Fallback Guarantee

Voice is strictly an enhancement. The application remains 100% usable on all browsers via the dedicated text input and dialogue cards if:
- Microphone permissions are denied or blocked.
- Browser does not implement `window.SpeechRecognition`.
- Regional voice packs are not installed on the user's operating system.
- Speech synthesis fails or is muted by the user.

---

## Current MVP Limitations

- **Browser-Native Web Speech**: Relies on browser-provided speech recognition and text-to-speech models rather than specialized low-resource dialect STT/TTS servers (e.g. Bhashini / Whisper).
- **Languages**: Currently supports English and Hindi. Regional languages (e.g. Marathi) will be added in future stages.
- **Recommendations Preview**: The current Results Page displays the synthesized profile. Integration with the deterministic NSQF matching endpoint will be connected in the subsequent phase.
