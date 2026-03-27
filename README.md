Anchor AI - "Ask anything. Anchored to everything."
Most LLM chatbots have a trust problem. Ask them anything, and they'll answer confidently, fluently, and sometimes completely wrong. AnchorAI is built around a different principle: an AI that only speaks from what it's been shown. Paste a URL or drop a document, and AnchorAI grounds every response in that source, citing the exact passage it used, refusing to speculate beyond it. No hallucinations. Full traceability. It's a small-scale demonstration of the core problem that Alactic Inc. is solving at enterprise scale: making AI responses not just fluent, but grounded and trustworthy.

Browser (anchorai.html)
    │
    ├── User loads URL  ──► POST /api/fetch-url  ──► httpx fetches it
    │                                             ──► BeautifulSoup cleans it
    │                                             ──► returns clean text
    │
    ├── User uploads PDF ──► POST /api/parse-pdf-file ──► PyMuPDF extracts it
    │                                                  ──► page by page, clean
    │                                                  ──► returns clean text
    │
    ├── User pastes text ──► handled entirely in browser, no server needed
    │
    └── User asks question ──► POST /api/ask ──► Gemini 2.5 Flash
                                              ──► grounded to source
                                              ──► returns JSON
                                              ──► { found, answer, excerpt, confidence }