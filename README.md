# AnchorAI — "Ask Anything. Anchored to Everything."

**AnchorAI** is a source-grounded LLM chatbot that solves the hallucination problem. Unlike traditional chatbots that confidently guess, AnchorAI *only* answers from sources you provide—citing the exact passage it used, with confidence scores, and refusing to speculate beyond what it's been shown.

> This is a demonstration of the core problem that **Alactic Inc.** is solving at enterprise scale: making AI responses not just fluent, but **grounded and trustworthy**.

---

## 🎯 The Problem AnchorAI Solves

Most LLM chatbots have a **trust problem**:
- ❌ They answer with false confidence, even when they don't know
- ❌ No way to verify or trace an answer back to a source
- ❌ Hallucinations undermine decision-making

**AnchorAI's approach**: Every answer is grounded in a source document. Ask it something it can't find? It says so honestly.

---

## ✨ Key Features

| Feature | What It Does |
|---------|-------------|
| **Source Grounding** | Answers only what exists in the provided source. No outside knowledge, no speculation. |
| **Exact Citation** | Every answer includes the verbatim excerpt from the source that supports it. |
| **Confidence Scoring** | Returns 0–100 score reflecting how directly the source supports the answer. |
| **Multiple Input Formats** | Load sources from URLs, PDF uploads, or paste text directly. |
| **Conversation Context** | Maintains conversation history for follow-up questions while staying grounded. |
| **Smart Text Extraction** | Uses BeautifulSoup for web pages and PyMuPDF for PDFs; removes noise (ads, nav, scripts). |
| **Safe Truncation** | Handles large documents by truncating at ~12,000 words to stay within LLM context limits. |

---

## 🏗️ Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      BROWSER (anchorai.html)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
   [Load URL]            [Upload PDF]            [Paste Text]
        │                       │                       │
        │                       │                    (handled
        │                       │                    locally,
        │                       │                    no server)
        │                       │
        └───────────────────────┼───────────────────────┘
                                │
                    (POST /api/fetch-url or
                   POST /api/parse-pdf-file)
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ▼                                               ▼
   ┌─────────────┐                             ┌─────────────┐
   │ BeautifulSoup│                             │  PyMuPDF    │
   │ HTML Parser │                             │ PDF Extract │
   └─────────────┘                             └─────────────┘
        │                                               │
        └───────────────────────┬───────────────────────┘
                                │
                        (clean text)
                                │
                                ▼
                    ┌──────────────────────┐
                    │  User asks question  │
                    │ (POST /api/ask)      │
                    └──────────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │  Gemini 2.5 Flash    │
                    │  (Grounding Engine)  │
                    └──────────────────────┘
                                │
                    (with SYSTEM_PROMPT
                     enforcing grounding)
                                │
                                ▼
                    ┌──────────────────────┐
                    │   JSON Response      │
                    │ {                    │
                    │   found: boolean,    │
                    │   answer: string,    │
                    │   excerpt: string,   │
                    │   confidence: 0-100  │
                    │ }                    │
                    └──────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Backend** | FastAPI (Python) |
| **LLM** | Google Gemini 2.5 Flash |
| **HTTP Client** | httpx (async) |
| **HTML Parsing** | BeautifulSoup4 |
| **PDF Extraction** | PyMuPDF (fitz) |
| **Server** | Uvicorn |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+**
- **Google API Key** for Gemini (get it from [AI Studio](https://aistudio.google.com/apikey))

### Installation

1. **Clone or download** the project:
   ```bash
   cd Alactic
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set your Gemini API key**:
   ```bash
   # On Windows (PowerShell):
   $env:GEMINI_API_KEY = "your-key-here"
   
   # On Windows (CMD):
   set GEMINI_API_KEY=your-key-here
   
   # On macOS/Linux:
   export GEMINI_API_KEY="your-key-here"
   ```

### Running the App

```bash
python main.py
```

The app will start on **http://localhost:8000**

You'll see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started server process [XXXX]
```

Open your browser to `http://localhost:8000` and start asking questions!

---

## 📖 Usage Guide

### 1. Load a Source

**Option A: From a URL**
- Click the "URL" tab
- Paste a link (e.g., Wikipedia article, blog post, news)
- Click "Fetch & Parse"
- AnchorAI extracts and cleans the text

**Option B: Upload a PDF**
- Click the "PDF" tab
- Drag-and-drop a PDF or click to upload
- Wait for text extraction
- AnchorAI processes page by page

**Option C: Paste Text**
- Click the "Text" tab
- Paste or type content directly
- Submit

### 2. Ask Questions

Once a source is loaded:
- Type your question in the chat input
- Press Enter or click Send
- AnchorAI replies with:
  - **Answer**: The direct answer from the source
  - **Excerpt**: The exact passage it cited
  - **Confidence**: 0–100 score of how well the source supports the answer
  - **Status**: "Anchored · Ready" (green dot) means it's grounded

### 3. Follow-Up Questions

Continue asking—AnchorAI maintains conversation history to understand context while staying grounded in the original source.

### 4. Reset

Click "Reset" to clear the source and start fresh.

---

## 🔌 API Reference

### `GET /`

Serves the frontend HTML.

**Response**: `text/html` (the AnchorAI interface)

---

### `POST /api/fetch-url`

Fetch and clean text from a URL.

**Request**:
```json
{
  "url": "https://example.com/article"
}
```

**Response** (200):
```json
{
  "content": "Clean extracted text...",
  "word_count": 1234,
  "url": "https://example.com/article"
}
```

**Error Responses**:
- `408 Request Timeout`: URL took too long to load
- `400 Bad Request`: Invalid URL
- `415 Unsupported Media Type`: Not HTML or plain text
- `422 Unprocessable Entity`: Page has too little content

---

### `POST /api/parse-pdf-file`

Extract text from an uploaded PDF.

**Request**: Multipart form data with file field:
```
Content-Type: multipart/form-data
file: <binary PDF data>
```

**Response** (200):
```json
{
  "content": "Full extracted text from all pages...",
  "page_count": 5,
  "word_count": 2500,
  "filename": "document.pdf"
}
```

**Error Responses**:
- `415 Unsupported Media Type`: Not a PDF
- `413 Payload Too Large`: PDF exceeds 20MB
- `422 Unprocessable Entity`: PDF corrupted or encrypted

---

### `POST /api/ask`

Answer a question grounded in a source.

**Request**:
```json
{
  "question": "What is the main topic?",
  "source": "The source document text...",
  "history": [
    {"role": "user", "content": "First question"},
    {"role": "assistant", "content": "First answer"}
  ]
}
```

**Response** (200):
```json
{
  "found": true,
  "answer": "The main topic is...",
  "excerpt": "Quoted verbatim from the source.",
  "confidence": 92
}
```

**When answer not found**:
```json
{
  "found": false,
  "answer": "",
  "excerpt": "",
  "confidence": 0
}
```

**Error Responses**:
- `400 Bad Request`: Source too short or question too short
- `502 Bad Gateway`: Gemini API error

---

## 🧠 How the Grounding Works

The magic is in the **SYSTEM_PROMPT**. When you ask a question, AnchorAI:

1. **Embeds your source** into the prompt
2. **Sends to Gemini** with explicit instructions:
   - ✅ Only use the source document
   - ✅ Return exact excerpts verbatim
   - ✅ Rate confidence honestly
   - ✅ Refuse gracefully if answer not in source
3. **Returns structured JSON** with `found`, `answer`, `excerpt`, and `confidence`
4. **Frontend displays** the answer with citation and provenance

**Key safeguards**:
- Low temperature (0.1) = more faithful, less creative
- Max tokens capped at 800
- System prompt is enforced before each request
- JSON validation ensures consistent output format

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key |

### Tuning Parameters (in `main.py`)

- **Context limit**: ~12,000 words (line 96)  
  → Increase/decrease in `extract_clean_text()` and `parse_pdf_file()`
- **Model temperature**: 0.1 (line 308)  
  → Lower = more faithful, higher = more creative
- **Max tokens**: 800 (line 309)  
  → Controls response length
- **PDF file size**: 20MB max (line 456)  
  → Increase/decrease as needed
- **History window**: Last 6 turns (line 295)  
  → Controls how much context is kept for follow-ups

---

## 📋 Project Structure

```
Alactic/
├── main.py                 # FastAPI backend + all API endpoints
├── anchorai.html           # Frontend (HTML/CSS/JS all-in-one)
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── startup.sh             # Optional: startup script
```

---

## 🐛 Troubleshooting

### API Key Error
```
ModuleNotFoundError: No module named 'google.generativeai'
```
**Fix**: Reinstall requirements:
```bash
pip install google-generativeai
```

### Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Fix**: Change port in `main.py` (last line) or kill the process:
```bash
# On Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# On macOS/Linux:
lsof -i :8000
kill <PID>
```

### PDF Won't Upload
- Check file is actual PDF (not image scan)
- Keep file under 20MB
- Scanned/image-based PDFs won't extract (need OCR separately)

### Gemini Returns Empty Answer
- Source text might be truncated (>12,000 words)
- Question might not be answerable from the source
- Check confidence score—if 0, answer isn't in source

---

## 🚢 Deployment

### Local Development
```bash
python main.py
```

### Production (Gunicorn + Uvicorn)
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Docker (Example)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV GEMINI_API_KEY=$GEMINI_API_KEY
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t anchorai .
docker run -e GEMINI_API_KEY=<your-key> -p 8000:8000 anchorai
```

---

## 📚 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.5 | Web framework |
| `uvicorn` | 0.32.1 | ASGI server |
| `httpx` | 0.28.0 | Async HTTP client (URL fetching) |
| `beautifulsoup4` | 4.12.3 | HTML parsing & cleaning |
| `google-generativeai` | 0.8.3 | Gemini API client |
| `python-multipart` | 0.0.12 | File upload handling |
| `pymupdf` | 1.24.11 | PDF text extraction |

---

## 🎓 Use Cases

- **Research**: Verify claims against source documents
- **Legal**: Answer questions only from specific contracts or policies
- **Customer Support**: Ground responses in knowledge base documents
- **Education**: Quiz students on specific readings without hallucination
- **News Analysis**: Ask questions about articles with exact citations
- **Documentation**: Query product manuals with confidence scores

---

## 🔐 Security Considerations

- **API Key**: Never commit `GEMINI_API_KEY` to version control. Use environment variables.
- **Input Validation**: All endpoints validate inputs and enforce size limits.
- **Error Handling**: Errors are caught and returned as JSON (no stack traces exposed).
- **CORS**: Configure as needed for cross-origin requests.
- **Rate Limiting**: Consider adding rate limiting for production.

---

## 📝 License

Built by **Alactic Inc.** as a demonstration of their technology. This is a sample project.

---

## 🤝 Contributing

Found a bug or want to improve AnchorAI? Open an issue or submit a pull request!

---

## 📧 Support

For questions or feedback, reach out through the official Alactic channels.