# AnchorAI
### *Ask anything. Anchored to everything.*

---

Most AI chatbots have a quiet problem nobody talks about. They answer everything — fluently, confidently, and sometimes completely wrong. You ask a question, you get an answer that sounds right, and you have no way of knowing whether it came from something real or was quietly invented. That gap between fluency and truth is what AnchorAI is designed to close.

The idea is simple. You give AnchorAI a source — a URL, a PDF, a block of text. From that point on, it only speaks from what it has been shown. Every answer comes with the exact sentence it pulled from. When something isn't in the source, it says so instead of guessing. No hallucinations. Full traceability.

It is a small-scale version of the same problem Alactic Inc. is solving at enterprise scale — making AI responses grounded in real, verifiable data rather than statistical confidence.

---

## Why it works differently

Every other chatbot is optimized to always have an answer. AnchorAI is optimized to know when it doesn't. That sounds like a limitation. It's actually the harder engineering problem — teaching a model to refuse gracefully is more interesting than teaching it to respond fluently.

The grounding behavior lives in the system prompt. When you ask a question, the entire source document is embedded into the context alongside a strict set of rules: only answer from this, return the exact excerpt you used, score your confidence honestly, and say nothing if the answer isn't here. Low temperature keeps the model faithful. Structured JSON output keeps the responses consistent and parseable. The result is a chatbot that behaves like a careful researcher rather than a confident guesser.

---

## What you can do with it

Load any of these as a source:

- A Wikipedia article or news page via URL
- A research paper, policy document, or manual as a PDF
- Any block of text pasted directly

Then ask questions in plain English. The right panel shows you the source excerpt alongside every answer, so you can verify it yourself. Ask something outside the source — you'll see the refusal in action. That moment is the point of the whole project.

---

## Tech stack

| Layer | Tool |
|---|---|
| Frontend | HTML, CSS, Vanilla JS — single file |
| Backend | FastAPI + Python |
| LLM | Google Gemini 2.5 Flash |
| URL fetching | httpx (async) |
| HTML cleaning | BeautifulSoup4 |
| PDF extraction | PyMuPDF |
| Server | Uvicorn |
| Hosting | Azure App Service |

The frontend and backend run from one server. No separate build step, no webpack, no framework overhead. The HTML file is served directly by FastAPI at the root route.

---

## Running it locally

You need Python 3.9+ and a free Gemini API key from [aistudio.google.com](https://aistudio.google.com/apikey).

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key (Windows PowerShell)
$env:GEMINI_API_KEY = "your-key-here"

# Run
python main.py
```

Open **http://localhost:8000** in your browser.

FastAPI generates live API documentation automatically at **http://localhost:8000/docs** — no extra work needed.

---

## How the grounding actually works

This is the part worth understanding if you want to know what's happening under the hood.

When you ask a question, the backend constructs a prompt that contains three things — the system instructions, the full source document, and your question. The system instructions tell Gemini to return a JSON object with four fields: `found` (boolean), `answer` (string), `excerpt` (verbatim quote from source), and `confidence` (0–100 integer). It is told explicitly that if the answer is not in the source, it sets `found` to false and leaves the other fields empty.

Temperature is set to 0.1. This is deliberate — lower temperature means the model sticks closer to what is in front of it and invents less. Max tokens is capped at 800, which is enough for a focused answer and excerpt but not enough to wander.

When the JSON comes back, the backend validates and sanitises the shape before sending it to the frontend. If the parse fails for any reason, it returns a safe `found: false` response rather than crashing. The frontend then renders the answer and the excerpt side by side so you can see exactly what grounded what.

---

## API reference

### `GET /`
Returns the frontend HTML.

---

### `POST /api/fetch-url`

Fetches a webpage and returns clean text — navigation, scripts, ads, and footers stripped out.

```json
// Request
{ "url": "https://example.com/article" }

// Response
{
  "content": "Extracted clean text...",
  "word_count": 1840,
  "url": "https://example.com/article"
}
```

---

### `POST /api/parse-pdf-file`

Accepts a PDF upload (multipart form data) and returns extracted text page by page.

```json
// Response
{
  "content": "Full document text...",
  "page_count": 12,
  "word_count": 4300,
  "filename": "report.pdf"
}
```

PDF size limit is 20MB. Image-based or scanned PDFs won't extract — only text-based PDFs are supported.

---

### `POST /api/ask`

The core endpoint. Takes a question, the source text, and optional conversation history. Returns a grounded answer.

```json
// Request
{
  "question": "What is the main argument?",
  "source": "The full source text...",
  "history": []
}

// Response when found
{
  "found": true,
  "answer": "The main argument is...",
  "excerpt": "Verbatim sentence from the source.",
  "confidence": 88
}

// Response when not found
{
  "found": false,
  "answer": "",
  "excerpt": "",
  "confidence": 0
}
```

---

## Project structure

```
anchorai/
├── main.py          — FastAPI backend, all three API endpoints
├── anchorai.html    — Complete frontend in one file
├── requirements.txt — Python dependencies
├── startup.sh       — Azure App Service startup command
└── README.md        — This file
```

---

## Deployment

Hosted on **Azure App Service**. The startup command is:

```
uvicorn main:app --host 0.0.0.0 --port 8000
```

`GEMINI_API_KEY` is set as an application environment variable in Azure Portal → Configuration → Application Settings.

For local development just run `python main.py`. For production with multiple workers:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

---

## Configuration

| Variable | Required | Where to get it |
|---|---|---|
| `GEMINI_API_KEY` | Yes | [aistudio.google.com](https://aistudio.google.com) — free |

Tunable parameters inside `main.py`:

- **Word limit per source** — 12,000 words
- **Temperature** — 0.1 (lower = more faithful, higher = more creative)
- **Max output tokens** — 800
- **Conversation history window** — last 6 turns
- **PDF size cap** — 20MB

---

## Troubleshooting

**`KeyError: GEMINI_API_KEY`** — the environment variable isn't set. Set it in the same terminal window you run the server from.

**Port 8000 already in use** — run `netstat -ano | findstr :8000` on Windows, find the PID, then `taskkill /PID <number> /F`.

**PDF shows no text** — the file is likely scanned or image-based. Only PDFs with actual embedded text layers work.

**Gemini returns an empty answer** — either the question is genuinely not in the source (confidence will be 0) or the source was truncated at 12,000 words.

**App loads on Azure but API calls fail** — check that `GEMINI_API_KEY` is set in Azure Portal → your app → Configuration → Application Settings.

---

## Dependencies

| Package | Version | What it does |
|---|---|---|
| fastapi | 0.115.5 | Web framework |
| uvicorn | 0.32.1 | ASGI server |
| httpx | 0.28.0 | Async HTTP client for URL fetching |
| beautifulsoup4 | 4.12.3 | Strips HTML noise from web pages |
| google-generativeai | 0.8.3 | Gemini API client |
| python-multipart | 0.0.12 | Handles PDF file uploads |
| pymupdf | 1.24.11 | Extracts text from PDFs |

---

*Built as part of the Alactic Inc. internship assignment. The project is a deliberate attempt to understand Alactic's core technical problem — data grounding — from the inside, at a scale that an intern can actually build and defend.*