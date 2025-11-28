# Windows Setup Issues & Solutions

## Current Status

✅ **Groq SDK**: Fixed (upgraded to 0.36.0)  
❌ **Tesseract**: Not installed on Windows  
❌ **Poppler**: Not installed on Windows  

## Problem

On Windows, installing Tesseract and Poppler is complex and not needed for deployment testing since:
- Deployment (Render/Railway) will use apt buildpack
- For actual deployment, the setup will work automatically

## Recommended Solutions

### Option 1: Use Pure Gemini Vision API (Simplest ✅)

**Pros:**
- Already working in your setup
- No local dependencies needed
- Works for both images and PDFs
- Deployment-ready

**How:**  
Set in `.env`:
```bash
LLM_PROVIDER=gemini
```

Then use your existing API endpoint or run:
```bash
python src/app.py
# Test: http://localhost:8001/docs
```

### Option 2: For Deployment (Groq + Pytesseract)

When deploying to Render/Railway, use this `render.yaml`:

```yaml
services:
  - type: web
    name: bill-extraction-api
    env: python
    buildCommand: |
      # Install system dependencies
      apt-get update
      apt-get install -y tesseract-ocr poppler-utils
      # Install Python packages
      pip install -r requirements.txt
    startCommand: uvicorn src.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: LLM_PROVIDER
        value: groq
```

On deployment, Tesseract + Poppler will auto-install via apt, and Groq will work perfectly!

### Option 3: Install on Windows (Optional, for local testing)

**Install Tesseract:**
1. Download: https://github.com/UB-Mannheim/tesseract/wiki  
2. Install .exe
3. Add to PATH: `C:\Program Files\Tesseract-OCR`

**Install Poppler:**
1. Download: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract and add `bin folder to PATH

## Recommendation

**For now:** Use Gemini Vision API (set `LLM_PROVIDER=gemini` in `.env`)  
**For deployment:** Use Groq + apt buildpack (will work automatically)

This way you can test everything locally without Windows dependency issues!
