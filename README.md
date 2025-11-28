# Bill Extraction API

AI-powered API for extracting line items from medical bills and invoices with high accuracy.

## Overview

This solution uses **Google Gemini Vision API** to extract line item details from multi-page medical bills. The system handles PDFs and images, classifies page types, and extracts structured data while preventing duplicates and ensuring all items are captured.

## Features

- ✅ Multi-page PDF and image support
- ✅ Automatic page type classification (Bill Detail, Final Bill, Pharmacy)
- ✅ Line item extraction with name, amount, rate, and quantity
- ✅ Duplicate detection and removal
- ✅ Token usage tracking
- ✅ RESTful API endpoint
- ✅ Comprehensive validation

## Architecture

```
┌─────────────────┐
│  Document URL   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Document Processor     │
│  - Download             │
│  - PDF → Images         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Extraction Engine      │
│  - Gemini Vision API    │
│  - Page-by-page extract │
│  - Token tracking       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Validator              │
│  - Detect duplicates    │
│  - Calculate totals     │
│  - Validate schema      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Structured Response    │
└─────────────────────────┘
```

## Setup

### Prerequisites

- Python 3.8+
- Google Gemini API key
- Poppler (for PDF processing)

### Installation

1. **Install Poppler** (required for PDF to image conversion):
   
   **Windows:**
   ```bash
   # Download from: https://github.com/oschwartz10612/poppler-windows/releases
   # Extract and add to PATH
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key:**
   ```bash
   # Copy example env file
   cp .env.example .env
   
   # Edit .env and add your Gemini API key
   # GEMINI_API_KEY=your_actual_api_key_here
   ```

## Usage

### Start the Server

```bash
python src/app.py
```

Server will start on `http://localhost:8000`

### API Endpoint

**POST** `/extract-bill-data`

**Request:**
```json
{
  "document": "https://example.com/bill.pdf"
}
```

**Response:**
```json
{
  "is_success": true,
  "token_usage": {
    "total_tokens": 1523,
    "input_tokens": 1245,
    "output_tokens": 278
  },
  "data": {
    "pagewise_line_items": [
      {
        "page_no": "1",
        "page_type": "Pharmacy",
        "bill_items": [
          {
            "item_name": "Livi 300mg Tab",
            "item_amount": 448.0,
            "item_rate": 32.0,
            "item_quantity": 14.0
          }
        ]
      }
    ],
    "total_item_count": 1
  }
}
```

### Testing with cURL

```bash
curl -X POST http://localhost:8000/extract-bill-data \
  -H "Content-Type: application/json" \
  -d '{
    "document": "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&st=2025-11-24T14%3A13%3A22Z&se=2026-11-25T14%3A13%3A00Z&sr=b&sp=r&sig=WFJYfNw0PJdZOpOYlsoAW0XujYGG1x2HSbcDREiFXSU%3D"
  }'
```

### Testing with Postman

Import the provided Postman collection: `postman_collection.json`

## Evaluation

Test on all training samples:

```bash
python scripts/evaluate_accuracy.py
```

This will:
- Process all PDFs in `TRAINING_SAMPLES/`
- Extract line items using the API
- Calculate accuracy metrics
- Generate report in `evaluation_results.json`

## Project Structure

```
datathon/
├── src/
│   ├── __init__.py
│   ├── app.py                  # FastAPI application
│   ├── models.py               # Pydantic data models
│   ├── prompts.py              # LLM prompts
│   ├── document_processor.py   # PDF/image handling
│   ├── extraction_engine.py    # Gemini API integration
│   └── validator.py            # Data validation
├── scripts/
│   └── evaluate_accuracy.py    # Evaluation script
├── tests/
├── TRAINING_SAMPLES/           # Training data
├── config.py                   # Configuration
├── requirements.txt            # Dependencies
├── .env.example                # Environment template
├── .env                        # Your config (gitignored)
└── README.md                   # This file
```

## Approach

### 1. Document Processing
- Download document from URL
- Detect format (PDF or image)
- Convert PDF pages to images
- Prepare for vision API

### 2. Extraction Strategy
- Use Gemini Vision API for native document understanding
- Page-by-page extraction to maintain context
- Structured prompting with examples
- Pass previous items to avoid duplicates

### 3. Validation & Cleanup
- Detect duplicate entries across pages
- Validate amount = rate × quantity
- Calculate total and item count
- Remove invalid entries

### 4. Optimization
- Use `gemini-2.5-flash` for speed and cost efficiency
- Low temperature (0.1) for consistent extraction
- Token tracking for cost monitoring
- Retry logic for API failures

## Configuration

Edit `.env` file:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
TEMPERATURE=0.1
API_PORT=8000
```

## Error Handling

The API returns appropriate error responses:

**400 Bad Request:**
```json
{
  "is_success": false,
  "message": "Document must be a valid URL"
}
```

**500 Internal Server Error:**
```json
{
  "is_success": false,
  "message": "Failed to process document. Internal server error occurred"
}
```

## Performance

- **Accuracy Target:** >95% (extracted total vs actual total)
- **Average Processing Time:** 10-20 seconds per document
- **Token Usage:** ~1000-3000 tokens per document
- **Supported Formats:** PDF, PNG, JPG, JPEG

## Future Enhancements

- [ ] Custom fine-tuned model for better accuracy
- [ ] OCR preprocessing for poor quality scans
- [ ] Caching for repeated documents
- [ ] Batch processing endpoint
- [ ] Confidence scores per item
- [ ] Support for more document types

## License

MIT

## Author

Created for HackRx Datathon - Bill Extraction Challenge
