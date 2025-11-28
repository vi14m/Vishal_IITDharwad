"""
Local OCR Engine using Hybrid Approach
1. Try PyMuPDF text extraction (instant for text-based PDFs)
2. Fall back to Pytesseract OCR (lightweight for scanned PDFs)
"""
import io
import numpy as np
from PIL import Image
from typing import List, Tuple, Any
import pytesseract


class LocalOCREngine:
    """Extract text from images/PDFs using hybrid approach"""
    
    def __init__(self):
        """Initialize OCR engine"""
        print("Initializing Local OCR Engine (PyMuPDF + Pytesseract)...")
        # Pytesseract doesn't need initialization
        print("OCR Engine initialized successfully")
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """
        Extract text from a PIL Image using Pytesseract
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text as string
        """
        try:
            # Use Pytesseract OCR
            print("\n" + "="*80)
            print("🔍 PYTESSERACT OCR - STARTING EXTRACTION")
            print("="*80)
            
            text = pytesseract.image_to_string(image)
            
            # Verification print
            print("\n✅ OCR EXTRACTION COMPLETE")
            print(f"📄 Extracted Text Length: {len(text)} characters")
            print("\n" + "-"*80)
            print("📋 EXTRACTED TEXT (First 500 characters):")
            print("-"*80)
            print(text[:500] if len(text) > 500 else text)
            if len(text) > 500:
                print("\n... (truncated for display, full text will be sent to LLM)")
            print("-"*80 + "\n")
            
            return text.strip()
        except Exception as e:
            print(f"❌ Warning: Pytesseract OCR failed ({e}). Returning empty text.")
            print("⚠️  Tesseract not installed. On deployment, use apt buildpack.")
            return ""
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF using hybrid approach:
        1. Try PyMuPDF text extraction (fast)
        2. Fall back to OCR if text extraction fails
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Extracted text as string
        """
        import fitz  # PyMuPDF
        
        print("\n" + "="*80)
        print("📑 PDF PROCESSING - Starting Hybrid Text Extraction")
        print("="*80)
        
        # Open PDF from bytes
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"📖 Total Pages: {len(pdf_document)}")
        
        all_text = []
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            print(f"\n📄 Processing Page {page_num+1}/{len(pdf_document)}...")
            
            # First, try to extract text directly (fast, works for text-based PDFs)
            page_text = page.get_text()
            
            # If no text or very little text, it's probably scanned - use OCR
            if len(page_text.strip()) < 50:  # Threshold for "empty" page
                print(f"   ↳ ⚠️  Low text content ({len(page_text.strip())} chars), using Pytesseract OCR...")
                # Render page to image for OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                page_text = self.extract_text_from_image(image)
            else:
                print(f"   ↳ ✅ Direct text extraction successful ({len(page_text.strip())} chars)")
                print(f"   ↳ Preview: {page_text.strip()[:100]}...")
            
            all_text.append(f"--- Page {page_num+1} ---\n{page_text}")
        
        pdf_document.close()
        
        combined_text = "\n\n".join(all_text)
        print("\n" + "="*80)
        print("✅ PDF EXTRACTION COMPLETE")
        print(f"📊 Total Text Extracted: {len(combined_text)} characters")
        print("="*80 + "\n")
        
        return combined_text
    
    def extract_text(self, content: Any, mime_type: str) -> str:
        """
        Extract text from content based on MIME type
        
        Args:
            content: File content (bytes for PDF, PIL.Image or bytes for images)
            mime_type: MIME type of the content
            
        Returns:
            Extracted text as string
        """
        if mime_type == "application/pdf":
            return self.extract_text_from_pdf(content)
        elif mime_type.startswith("image/"):
            # Handle both PIL Image objects and raw bytes
            if isinstance(content, Image.Image):
                # Already a PIL Image, use directly
                return self.extract_text_from_image(content)
            else:
                # Raw bytes, convert to PIL Image first
                image = Image.open(io.BytesIO(content))
                return self.extract_text_from_image(image)
        else:
            raise ValueError(f"Unsupported MIME type: {mime_type}")
    
    def optimize_text_for_llm(self, text: str, max_chars: int = 15000) -> str:
        """
        Optimize extracted text to reduce token usage
        
        Strategies:
        1. Remove excessive whitespace
        2. Deduplicate repeated lines
        3. Truncate if too long (with smart truncation)
        
        Args:
            text: Raw OCR text
            max_chars: Maximum character count (approximate token limit * 4)
            
        Returns:
            Optimized text
        """
        # Remove excessive whitespace
        lines = text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        # Deduplicate consecutive identical lines
        deduplicated = []
        prev_line = None
        for line in lines:
            if line != prev_line:
                deduplicated.append(line)
                prev_line = line
        
        text = '\n'.join(deduplicated)
        
        # Truncate if too long (keep beginning and end)
        if len(text) > max_chars:
            print(f"Text too long ({len(text)} chars), truncating to {max_chars} chars...")
            # Keep first 80% and last 20%
            keep_start = int(max_chars * 0.8)
            keep_end = max_chars - keep_start
            text = text[:keep_start] + "\n\n[... TRUNCATED ...]\n\n" + text[-keep_end:]
        
        return text
