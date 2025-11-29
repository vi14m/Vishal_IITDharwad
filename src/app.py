"""
Bill Extraction API Server
FastAPI application for extracting line items from medical bills
"""
import traceback
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import config
from src.models import (
    DocumentRequest, 
    ExtractionResponse, 
    ErrorResponse,
    ExtractionData,
    TokenUsage
)
from src.document_processor import DocumentProcessor
from src.extraction_engine import ExtractionEngine
from src.validator import Validator


# Initialize FastAPI app
app = FastAPI(
    title="Bill Extraction API",
    description="Extract line items from medical bills using AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Bill Extraction API",
        "version": "1.0.0"
    }


@app.post("/extract-bill-data", response_model=ExtractionResponse)
async def extract_bill_data(
    document: str = Form(None),
    file: UploadFile = File(None)
):
    """
    Extract line items from a bill document
    
    Args:
        document: Optional URL to the document (PDF or image)
        file: Optional uploaded file (PDF or image)
    
    Returns:
        ExtractionResponse with extracted data and token usage
    """
    try:
        # Validate configuration
        config.validate()
        
        # Debug: Log what we received
        print(f"DEBUG: Received document={document}, file={file}, file.filename={file.filename if file else 'None'}")
        
        # Properly check if file was actually uploaded
        has_file = file is not None and file.filename is not None and file.filename != ""
        has_document = document is not None and document != ""
        
        # Validate that exactly one input method is provided
        if has_document and has_file:
            raise HTTPException(
                status_code=400,
                detail="Please provide either 'document' URL or 'file' upload, not both"
            )
        
        if not has_document and not has_file:
            raise HTTPException(
                status_code=400,
                detail="Please provide either 'document' URL or 'file' upload"
            )
        
        # Initialize components
        doc_processor = DocumentProcessor(timeout=config.REQUEST_TIMEOUT)
        extraction_engine = ExtractionEngine()
        validator = Validator()
        
        # Step 1: Process document based on input type
        if document:
            # URL-based processing
            print(f"Processing document from URL: {document}")
            content, mime_type, page_count = doc_processor.process_document(document)
        else:
            # File upload processing
            print(f"Processing uploaded file: {file.filename}")
            content = await file.read()
            content, mime_type, page_count = doc_processor.process_file_content(content)
        
        print(f"Document has {page_count} page(s)")
        
        # Step 2: Extract bill items from document
        print("Extracting bill items...")
        pagewise_items, token_usage = extraction_engine.extract_from_document(content, mime_type)
        print(f"Extracted {len(pagewise_items)} page(s) with items")
        
        # Step 3: Validate and clean data
        print("Validating extracted data...")
        validation_report = validator.validate_all(pagewise_items)
        
        # Log validation results
        if validation_report["warnings"]:
            print("Warnings:")
            for warning in validation_report["warnings"]:
                print(f"  - {warning}")
        
        if validation_report["duplicates"]:
            print(f"Found {len(validation_report['duplicates'])} potential duplicates")
            # Remove duplicates
            pagewise_items = validator.remove_duplicates(pagewise_items)
            print("Duplicates removed")
        
        # Recalculate item count after deduplication
        total_item_count = validator.count_total_items(pagewise_items)
        total_amount = validator.calculate_total(pagewise_items)
        
        print(f"Final: {total_item_count} items, Total amount: {total_amount}")
        
        # Step 4: Build response
        extraction_data = ExtractionData(
            pagewise_line_items=pagewise_items,
            total_item_count=total_item_count
        )
        
        response = ExtractionResponse(
            is_success=True,
            token_usage=token_usage,
            data=extraction_data
        )
        
        return response
        
    except ValueError as e:
        # Validation or processing error
        print(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
    except Exception as e:
        # Internal server error
        print(f"Internal error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document. Internal server error occurred: {str(e)}"
        )



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler to match required error response format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "is_success": False,
            "message": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "is_success": False,
            "message": f"Internal server error: {str(exc)}"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Bill Extraction API Server")
    print("=" * 60)
    print(f"Starting server on {config.API_HOST}:{config.API_PORT}")
    print(f"Using model: {config.GEMINI_MODEL}")
    print(f"Config loaded from: {config}")
    print("=" * 60)
    
    uvicorn.run(
        "src.app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )
