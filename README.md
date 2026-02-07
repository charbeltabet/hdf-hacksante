# HSante

> AI-powered medical intake automation — from any input to a filled DxCare form in seconds.

![chat_hero](./read_me_assets/chat_hero.png)
![result_hero](./read_me_assets/result_form.png)

---

## The Problem

Hospital intake is slow. Clinicians manually transcribe patient information from handwritten notes, scanned documents, voice recordings, and conversations into DxCare forms — a repetitive, error-prone process that eats into care time.

## The Solution

HSante accepts **any input** — text, photos, PDFs, spreadsheets, voice recordings, or a live AI-guided conversation — extracts structured medical data using LLMs, and **automatically fills the DxCare form** via desktop automation.

---

## Features

### 5 Input Modes

#### Chat Mode — Conversational Data Collection

The flagship feature. An AI assistant conducts a structured medical interview, adapting its tone based on who it's talking to:

- **Patient mode** — friendly, empathetic, uses simple language
- **Doctor mode** — professional, concise, uses medical terminology

Real-time **field progress pills** show which data has been collected (green) and what's still needed (gray). Every AI response is streamed token-by-token and **read aloud via TTS** with a mute toggle. Users can reply by typing or tapping the **mic button** for voice input.

![chat_feature](./read_me_assets/chat_feature.png)

![chat_voice](./read_me_assets/chat_voice.png)

#### Text Mode — Paste & Parse

Paste clinical notes, referral letters, or any freeform text. The LLM extracts all relevant fields in one shot.

![text_mode](./read_me_assets/text_node_feature.png)

#### Camera Mode — Snap a Document

Point your phone camera at a prescription, lab report, or handwritten note. The app captures a photo, sends it to a vision model (Gemini 2.5 Pro), and extracts structured data from the image.

![camera_mode](./read_me_assets/camera_feature.png)

#### Upload Mode — Drag & Drop Files

Drag and drop or browse for files. Supports:

| Format | Examples |
|--------|----------|
| Images | PNG, JPG, WEBP, GIF, BMP |
| Documents | PDF (multi-page, converted page-by-page) |
| Spreadsheets | CSV, Excel (.xlsx, .xls) |
| Data | JSON |

![upload_mode](./read_me_assets/file_upload_feature.png)

#### Voice Mode — Record & Transcribe

Hit record, describe the patient context verbally, and the app transcribes (Deepgram Nova-3) then parses the transcript into structured fields. A live timer and animated visualizer bars give real-time feedback.

---

### Smart Extraction with Reasoning

Every extraction shows **what** was extracted and **why**. The AI provides chain-of-thought reasoning explaining its decisions, visible in an expandable section on the results card. All extracted fields are **editable** before confirmation.

![chatting_flow](./read_me_assets/chat_flow.png)

---

### One-Click Form Filling

Once you confirm the extracted data, HSante switches to the DxCare window and **automatically fills every field** — text inputs, searchable dropdowns, and checkbox groups — using desktop automation (PyAutoGUI).

![received_info](./read_me_assets/received_info.png)
![dx_care_filled](./read_me_assets/dx_care_filled.png)

---

## How Form Filling Works

The core trick: we decouple **what data the form needs** from **where to click on screen** using a two-file system.

```mermaid
flowchart TD
    A["🏥 DxCare Form<br/>(desktop app)"] --> B["questionaire.json<br/><b>Form Definition</b><br/>fields + coordinates + field types"]

    B -->|"generate_json_schema()"| C["questionaire_schema.json<br/><b>JSON Schema</b><br/>fields + types + enums<br/>(no coordinates)"]

    C -->|"fed to LLM as target schema"| D["AI Extraction<br/>(DSPy / Chat)"]

    D -->|"returns structured data"| E["form_data<br/>{field: value, ...}"]

    E -->|"fill_form_with_data()"| F["Form Filler<br/>(PyAutoGUI)"]

    B -->|"provides coordinates"| F

    F -->|"click + type at x,y"| A

    style A fill:#e8f4fd,stroke:#2196F3
    style B fill:#fff3e0,stroke:#FF9800
    style C fill:#fff3e0,stroke:#FF9800
    style D fill:#e8f5e9,stroke:#4CAF50
    style E fill:#e8f5e9,stroke:#4CAF50
    style F fill:#fce4ec,stroke:#E91E63
```

### The Two JSON Files

**`questionaire.json`** — Form Definition (with coordinates)

You map each DxCare field once by recording its pixel coordinates, field type, and label. Three field types are supported:

| Field Type | Coordinates | How it fills |
|---|---|---|
| `form_input` | Single `x, y` | Click → type value |
| `searchable_select` | `dropdown`, `input`, `result` (3 coordinate pairs) | Open dropdown → type search → click result |
| `checkbox_group` | `x, y` per option | Click each matching checkbox |

**`questionaire_schema.json`** — JSON Schema (no coordinates)

Auto-generated from the form definition by stripping out all coordinates. This is what the LLM sees — just field names, types, descriptions, and enum options. The LLM never knows about pixel positions.

### The Pipeline

1. **Map once** — Record DxCare field coordinates into `questionaire.json`
2. **Generate schema** — Run `form_schema_generator.py` to strip coordinates → `questionaire_schema.json`
3. **Extract data** — LLM parses any input against the schema → `{field: value}` dict
4. **Fill form** — `fill_form_with_data()` joins the extracted values back with coordinates and drives PyAutoGUI to click and type into DxCare

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │           Frontend (Vanilla JS)       │
                    │  5 modes · Markdown · TTS playback    │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │           Flask Backend               │
                    │                                       │
                    │  /parse-context ──► Parser Router     │
                    │       ├─ Text    → DSPy + GPT-OSS     │
                    │       ├─ Image   → DSPy + Gemini 2.5  │
                    │       ├─ Audio   → Deepgram STT → Text│
                    │       ├─ PDF     → PyMuPDF → Image    │
                    │       ├─ CSV/XLS → Pandas → Text      │
                    │       └─ JSON    → Text               │
                    │                                       │
                    │  /chat-*  ──► SSE streaming (GPT-4o)  │
                    │  /tts     ──► Deepgram TTS            │
                    │  /stt     ──► Deepgram STT            │
                    │  /fill-form ─► PyAutoGUI              │
                    └───────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │         External Services             │
                    │  OpenRouter · Deepgram · Cloudflare R2│
                    └──────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python) |
| Frontend | Vanilla JS, CSS (no frameworks) |
| LLM Orchestration | DSPy (ChainOfThought) |
| Chat Model | GPT-4o-mini via OpenRouter |
| Text Extraction | GPT-OSS-120B via OpenRouter |
| Vision | Gemini 2.5 Pro via OpenRouter |
| Voice | Deepgram (Nova-3 STT + Aura-2 TTS) |
| File Storage | Cloudflare R2 |
| Form Automation | PyAutoGUI |
| PDF Processing | PyMuPDF |
| Spreadsheets | Pandas + openpyxl |

## Getting Started

```bash
# Clone
git clone <repo-url>
cd hsante

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in: OPENROUTER_API_KEY, DEEPGRAM_API_KEY, R2 credentials

# Run
python app.py
```

Open `http://localhost:5000/form-context` in your browser.

## Medical Fields Collected

The system extracts data matching a DxCare intake like the following:

- **Reason of Hospitalization** — why the patient came
- **History of Illness** — symptoms and timeline
- **Habitual Treatment** — regular medications (structured + freetext)
- **Specific Procedures** — e.g. anticoagulant protocols
- **Blood Tests** — bacteriology, biochemistry, hematology, histopathology
- **Imaging Tests** — echography, MRI, radiography, scintigraphy, CT scan
- **Documents Brought** — discharge summaries, prescriptions, medical reports

---

*Built at a hackathon — because clinicians deserve better tools.*
