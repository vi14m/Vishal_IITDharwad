# Quick Start Guide

## ✅ What's Working Now

Your bill extraction API is **running on http://localhost:8000**!

### Current Configuration
- **LLM Provider**: Groq (fast, free)
- **OCR**: Pytesseract + PyMuPDF hybrid
- **API**: FastAPI running on port 8000

---

## 🧪 Test the API

### Option 1: Web UI (Easiest)
Visit: **http://localhost:8000/docs**

###Option 2: Python Test Script

```python
import requests

url = "http://localhost:8000/extract-from-file"

# Upload a PDF
with open("TRAINING_SAMPLES/train_sample_1.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)

print(response.json())
```

---

## ⚠️ Windows Dependency Issues (Expected)

**Tesseract & Poppler** are not installed on Windows → OCR will fail locally

**Solutions:**

1. **For Local Testing**: Use Gemini Vision API (works without OCR)
   - Set in `.env`: `LLM_PROVIDER=gemini`
   - Restart server

2. **For Deployment**: Use Groq + apt buildpack (auto-installs dependencies)
   - Already configured in [`render.yaml`](file:///d:/Projects/datathon/render.yaml)
   - Will work perfectly on Render/Railway

---

## 🚀 Deploy to Render

1. Push code to GitHub
2. Connect to Render.com
3. Add `GROQ_API_KEY` in environment variables
4. Deploy! (Tesseract installs automatically via `render.yaml`)

---

## 📊 Verification Output

When working, you'll see:
```
================================================================================
🔍 PYTESSERACT OCR - STARTING EXTRACTION
================================================================================
✅ OCR EXTRACTION COMPLETE
📄 Extracted Text Length: 1247 characters

================================================================================
📝 OPTIMIZED TEXT BEING SENT TO LLM:
================================================================================
[Bill text preview...]

================================================================================
🤖 GROQ API - STARTING STRUCTURED EXTRACTION
================================================================================
✅ GROQ EXTRACTION COMPLETE
💰 Tokens Used: 1534 (In: 1248, Out: 286)

================================================================================
📊 EXTRACTED STRUCTURED DATA:
================================================================================
{
  "pagewise_line_items": [
    {
      "page_no": "1",
      "page_type": "Pharmacy",
      "bill_items": [...]
    }
  ]
}
```

---

## Next Steps

1. ✅ API is running at http://localhost:8000
2. ⏳ Test with Gemini Vision (set `LLM_PROVIDER=gemini` in `.env`)
3. ⏳ Deploy to Render for full OCR+Groq pipeline  
4. ⏳ Evaluate accuracy on training samples
