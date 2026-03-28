import os
import json
import re
import httpx
import google.generativeai as genai
import fitz  # PyMuPDF

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware  
from pydantic import BaseModel
from bs4 import BeautifulSoup


# ─── APP SETUP ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AnchorAI",
    description="Source-grounded LLM chatbot. Every answer is traceable to a source document.",
    version="1.0.0"
)
# Enable CORS for frontend on any origin (safe for student project).
# This allows requests from localhost:3000, any other domain, etc.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for student project
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set. "
        "Get a free key at aistudio.google.com"
    )
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")


# ─── REQUEST MODELS ───────────────────────────────────────────────────────────

class FetchURLRequest(BaseModel):
    url: str

class AskRequest(BaseModel):
    question: str
    source: str
    history: list[dict] = []


# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────
# This is the core of AnchorAI. The entire grounding behavior lives here.
# It instructs Gemini to:
#   (1) Only answer from the provided source
#   (2) Always return the exact excerpt it used
#   (3) Return a confidence score reflecting how well the source supports the answer
#   (4) Refuse gracefully when the answer is not in the source

SYSTEM_PROMPT = """
You are AnchorAI — a question-answering assistant with one strict rule:
you ONLY answer from the SOURCE DOCUMENT provided by the user.
You never use outside knowledge, never speculate, and never hallucinate.

Your output must ALWAYS be a valid JSON object in this exact format:

{
  "found": true or false,
  "answer": "your answer here, or empty string if not found",
  "excerpt": "the exact sentence or passage from the source that supports your answer, or empty string if not found",
  "confidence": a number from 0 to 100 reflecting how directly the source supports the answer
}

Rules you must follow without exception:
- If the answer exists in the source: set found=true, write a clear answer, paste the supporting excerpt verbatim, and score your confidence honestly.
- If the answer is NOT in the source: set found=false, leave answer and excerpt as empty strings, set confidence to 0.
- Never invent or infer beyond what the source explicitly states.
- The excerpt must be copied word-for-word from the source — do not paraphrase it.
- Return ONLY the JSON object. No preamble, no markdown, no explanation outside the JSON.
""".strip()


# ─── UTILITY: CLEAN TEXT EXTRACTION ──────────────────────────────────────────
# Strips HTML to clean readable text — removes nav, footer, scripts, ads.
# This is the "ingestion" step. The cleaner the input, the better the grounding.

def extract_clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript", "iframe", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # Collapse whitespace and blank lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if len(line) > 30]  # drop short fragments
    clean = "\n".join(lines)

    # Truncate to ~12,000 words to stay within Gemini's context safely
    words = clean.split()
    if len(words) > 12000:
        clean = " ".join(words[:12000]) + "\n\n[Source truncated for processing]"

    return clean


# ─── UTILITY: SAFE JSON PARSE ─────────────────────────────────────────────────
# Gemini sometimes wraps JSON in markdown code fences. This strips them cleanly.

def parse_llm_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    return json.loads(cleaned)


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    """Serve the AnchorAI frontend."""
    return FileResponse("anchorai.html")
@app.get("/health")
async def health_check():
    """
    Health check endpoint for Azure App Service and load balancers.
    Returns 200 if the app is running and responsive.
    """
    return {"status": "ok", "service": "AnchorAI"}

@app.post("/api/fetch-url")
async def fetch_url(request: FetchURLRequest):
    """
    Fetch a URL and return clean, extracted text.
    This is the Connect + Process stage — raw web content in, clean text out.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(request.url, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="URL fetch timed out. Try pasting the text directly.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Could not fetch URL.")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL or unreachable page.")

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        raise HTTPException(status_code=415, detail="Only HTML and plain text pages are supported.")

    clean_text = extract_clean_text(response.text)

    if len(clean_text.strip()) < 100:
        raise HTTPException(status_code=422, detail="Page has too little readable content. Try pasting the text directly.")

    return {
        "content": clean_text,
        "word_count": len(clean_text.split()),
        "url": str(response.url)
    }


@app.post("/api/ask")
async def ask(request: AskRequest):
    """
    Answer a question, grounded strictly in the provided source.
    Returns the answer, the supporting excerpt, and a confidence score.
    This is the Transform stage — source + question in, structured intelligence out.
    """
    if not request.source or len(request.source.strip()) < 50:
        raise HTTPException(status_code=400, detail="Source content is too short.")

    if not request.question or len(request.question.strip()) < 2:
        raise HTTPException(status_code=400, detail="Question is too short.")

    # Build conversation context from recent history
    history_text = ""
    if request.history:
        turns = []
        for turn in request.history[-6:]:  # last 3 exchanges max
            role = "User" if turn["role"] == "user" else "AnchorAI"
            turns.append(f"{role}: {turn['content']}")
        history_text = "\n".join(turns) + "\n\n"

    # Compose the full prompt
    prompt = f"""{SYSTEM_PROMPT}

---SOURCE DOCUMENT START---
{request.source}
---SOURCE DOCUMENT END---

{history_text}User question: {request.question}

Respond with ONLY the JSON object."""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,       # low temperature = more faithful, less creative
                max_output_tokens=800,
            )
        )
        raw = response.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

    try:
        result = parse_llm_json(raw)
    except json.JSONDecodeError:
        # Fallback: if JSON parsing fails, return a safe not-found response
        return {
            "found": False,
            "answer": "",
            "excerpt": "",
            "confidence": 0
        }

    # Validate and sanitise the result shape
    return {
        "found": bool(result.get("found", False)),
        "answer": str(result.get("answer", "")),
        "excerpt": str(result.get("excerpt", "")),
        "confidence": min(100, max(0, int(result.get("confidence", 0))))
    }


# ─── PDF PARSING ──────────────────────────────────────────────────────────────

from fastapi import UploadFile, File

@app.post("/api/parse-pdf-file")
async def parse_pdf_file(file: UploadFile = File(...)):
    """
    Receive a PDF file, extract clean text page by page, return as string.
    This is AnchorAI's ingestion layer for document uploads.
    """

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted here.")

    contents = await file.read()

    # Safety cap — 20MB max
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF too large. Please use a file under 20MB.")

    try:
        doc = fitz.open(stream=contents, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=422, detail="Could not read PDF. File may be corrupted or encrypted.")

    pages_text = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages_text.append(f"[Page {page_num + 1}]\n{text}")

    doc.close()

    if not pages_text:
        raise HTTPException(
            status_code=422,
            detail="No readable text found. This PDF may be scanned or image-based."
        )

    full_text = "\n\n".join(pages_text)

    # Truncate to ~12,000 words — same cap as URL fetcher, keeps behavior consistent
    words = full_text.split()
    if len(words) > 12000:
        full_text = " ".join(words[:12000]) + "\n\n[Document truncated for processing]"

    return {
        "content": full_text,
        "page_count": len(pages_text),
        "word_count": len(full_text.split()),
        "filename": file.filename
    }


# ─── STARTUP ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)