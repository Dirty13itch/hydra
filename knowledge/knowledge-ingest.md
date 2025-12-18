# Knowledge Ingest Pipeline - Hydra Cluster

## Overview

The Unified Ingest Pipeline enables ingesting various content types (files, URLs, clipboard images, text) into Hydra's knowledge system with AI-powered analysis.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Content Sources                              │
├────────────┬────────────┬────────────┬────────────┬─────────────┤
│   Files    │    URLs    │  Clipboard │    Text    │    API      │
│  (Upload)  │  (GitHub,  │  (Images,  │  (Notes,   │  (Direct)   │
│            │   arXiv)   │ Screenshots│  Excerpts) │             │
└─────┬──────┴─────┬──────┴─────┬──────┴─────┬──────┴──────┬──────┘
      │            │            │            │             │
      └────────────┴────────────┼────────────┴─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Unified Ingest Pipeline                         │
│                  (unified_ingest.py)                             │
├─────────────────────────────────────────────────────────────────┤
│  1. Content Detection (MIME type, file extension)               │
│  2. Text Extraction (PyMuPDF for PDFs)                         │
│  3. Vision Analysis (LLaVA 7B for images)                       │
│  4. Content Analysis (qwen2.5:7b via Ollama)                    │
│  5. SSE Progress Streaming                                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Analysis Output                             │
├─────────────────────────────────────────────────────────────────┤
│  - Summary (concise overview)                                    │
│  - Key Insights (bullet points)                                  │
│  - Relevance to Hydra (how it connects to the project)          │
│  - Action Items (suggested next steps)                           │
│  - Tags (auto-generated keywords)                                │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest` | POST | Upload file for ingestion |
| `/ingest` | GET | List all ingested items |
| `/ingest/url` | POST | Ingest URL content |
| `/ingest/clipboard` | POST | Ingest clipboard image |
| `/ingest/text` | POST | Ingest text content |
| `/ingest/{item_id}` | GET | Get item status/details |
| `/ingest/{item_id}/stream` | GET | SSE progress stream |
| `/ingest/stats/summary` | GET | Ingestion statistics |

## Content Types Supported

### Files
- **Images**: PNG, JPG, JPEG, GIF, WebP, SVG
- **Documents**: PDF, TXT, MD, DOC, DOCX
- **Code**: PY, JS, TS, JSX, TSX, JSON, YAML, YML, CSS, HTML, XML, CSV

### URLs
- **Web Pages**: Any HTTP/HTTPS URL
- **GitHub**: Repository pages, files, READMEs
- **arXiv**: Paper abstracts and PDFs

### Clipboard
- **Images**: Screenshots, copied images
- Captured via browser Clipboard API

### Text
- **Notes**: Research notes, meeting summaries
- **Excerpts**: Article excerpts, code snippets

## Vision API Integration

Images are processed through the Vision API (LLaVA 7B) for:
- **Description**: Natural language description of image content
- **OCR**: Text extraction from screenshots/documents
- **Analysis**: Detailed visual analysis

```python
# Vision API call example
response = requests.post(
    "http://192.168.1.244:8700/vision/describe",
    json={"image": base64_data, "prompt": "Describe this image"}
)
```

## Processing Pipeline

### Step 1: Content Detection
```python
# Detect content type from MIME or extension
content_type = detect_content_type(file)
# Returns: "image", "pdf", "document", "code", "url", "text"
```

### Step 2: Text Extraction
- **PDFs**: PyMuPDF extracts text from all pages
- **Images**: Vision API OCR extracts visible text
- **Code/Text**: Direct text content

### Step 3: Vision Analysis (Images Only)
```python
# LLaVA 7B via Ollama
description = await vision_describe(base64_image)
ocr_text = await vision_ocr(base64_image)
```

### Step 4: Content Analysis
```python
# qwen2.5:7b analyzes content for Hydra relevance
analysis = await analyze_content(
    text=extracted_text,
    content_type=content_type,
    topic=optional_topic
)
# Returns: summary, key_insights, relevance_to_hydra, action_items, tags
```

### Step 5: SSE Progress Streaming
```javascript
// Client-side subscription
const eventSource = new EventSource(`/ingest/${itemId}/stream`);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data: { id, status, progress, step }
};
```

## Command Center Integration

### IngestDropZone Component
Location: `src/hydra-command-center/components/IngestDropZone.tsx`

Features:
- **Browse Files**: Click button to select files
- **Drag & Drop**: Drop files onto the zone
- **Clipboard Paste**: Ctrl+V or Paste button
- **URL Input**: Enter URL and press Enter
- **Text Input**: Paste text with optional title
- **Topic Filter**: Optional topic for focused analysis
- **Real-time Progress**: SSE-powered status updates
- **Expandable Cards**: Click to view full analysis
- **Copy Buttons**: Quick copy for all fields
- **History**: LocalStorage persistence (50 items max)
- **Clear History**: Confirmation modal

### Knowledge View Integration
Location: `src/hydra-command-center/views/Knowledge.tsx`

The Ingest tab is accessible from the Knowledge view header.

## Usage Examples

### File Upload (cURL)
```bash
curl -X POST http://192.168.1.244:8700/ingest \
  -F "file=@document.pdf" \
  -F "topic=AI Infrastructure"
```

### URL Ingestion
```bash
curl -X POST http://192.168.1.244:8700/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/anthropics/anthropic-cookbook"}'
```

### Clipboard Image
```bash
curl -X POST http://192.168.1.244:8700/ingest/clipboard \
  -H "Content-Type: application/json" \
  -d '{"image": "data:image/png;base64,iVBORw0...", "topic": "UI Screenshots"}'
```

### Text Content
```bash
curl -X POST http://192.168.1.244:8700/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"content": "Meeting notes...", "title": "Weekly Standup"}'
```

### Check Status
```bash
curl http://192.168.1.244:8700/ingest/abc123
```

### Get Statistics
```bash
curl http://192.168.1.244:8700/ingest/stats/summary
# Returns: total, by_status, by_content_type, by_source
```

## Data Storage

### Uploaded Files
- Location: `data/ingest/` (gitignored)
- Format: `{item_id}_{filename}`

### Item Metadata
- Stored in-memory during processing
- Persisted to API for retrieval

### Browser History
- LocalStorage key: `hydra-ingest-history`
- Max items: 50
- Only completed items persisted

## Error Handling

### Common Errors
| Error | Cause | Resolution |
|-------|-------|------------|
| Vision API unavailable | Ollama not running | Check Ollama on hydra-compute |
| PDF extraction failed | Corrupted PDF | Try re-uploading or different format |
| Analysis timeout | Large content | Increase timeout or split content |

### Retry Mechanism
Failed items can be removed and re-uploaded through the UI.

## Performance

### Typical Processing Times
| Content Type | Size | Time |
|--------------|------|------|
| Image (screenshot) | 3840x2076 | ~3s |
| PDF (10 pages) | 800KB | ~5s |
| URL (web page) | - | ~4s |
| Text (1000 chars) | - | ~2s |

### Dependencies
- **PyMuPDF**: PDF text extraction
- **LLaVA 7B**: Vision model (Ollama)
- **qwen2.5:7b**: Analysis model (Ollama)

## Related Systems

- **Agentic RAG**: `/agentic-rag/*` - Query ingested knowledge
- **Graphiti**: `/graphiti/*` - Graph-based knowledge storage
- **Qdrant**: Vector storage for semantic search
- **Vision API**: `/vision/*` - Standalone image analysis
