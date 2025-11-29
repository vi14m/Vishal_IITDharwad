"""
Bill extraction engine using Google Gemini API
"""
import json
import time
import tempfile
import os
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from PIL import Image

from config import config
from src.models import PageWiseLineItem, BillItem, TokenUsage
from src.prompts import (
    get_extraction_prompt, 
    SYSTEM_PROMPT, 
    FULL_DOCUMENT_PROMPT
)


class ExtractionEngine:
    """Extract bill data using Gemini Vision API"""
    
    def __init__(self):
        """Initialize Gemini API"""
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        
        print(f"ExtractionEngine using model: {config.GEMINI_MODEL}")
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config={
                "temperature": config.TEMPERATURE,
                "max_output_tokens": config.MAX_TOKENS,
            }
        )
        
        self.total_token_usage = TokenUsage()
    
    def _extract_json_from_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from response text, handling markdown code blocks"""
        text = text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```
        
        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to find JSON object in text
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end+1])
                except:
                    pass
            
            # Provide helpful error message with context
            error_pos = getattr(e, 'pos', 0)
            context_start = max(0, error_pos - 100)
            context_end = min(len(text), error_pos + 100)
            context = text[context_start:context_end]
            
            print(f"ERROR: JSON parsing failed at position {error_pos}")
            print(f"Context: ...{context}...")
            print(f"Full response length: {len(text)} characters")
            
            raise ValueError(f"Failed to parse JSON from response: {e}. This may be due to response truncation. Try increasing MAX_TOKENS or simplifying the document.")
    
    def _update_token_usage(self, response) -> TokenUsage:
        """Extract token usage from Gemini response"""
        try:
            usage = TokenUsage()
            
            # Debug: Print available attributes on response
            # print(f"Debug: Response attributes: {dir(response)}")
            
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                metadata = response.usage_metadata
                usage.input_tokens = getattr(metadata, 'prompt_token_count', 0)
                usage.output_tokens = getattr(metadata, 'candidates_token_count', 0)
                usage.total_tokens = getattr(metadata, 'total_token_count', 0)
                
                # If total not provided, calculate it
                if usage.total_tokens == 0:
                    usage.total_tokens = usage.input_tokens + usage.output_tokens
            else:
                print("Warning: response.usage_metadata is None or missing")
                # Try to get usage from result if available (sometimes different structure)
                if hasattr(response, 'result') and hasattr(response.result, 'usage_metadata'):
                     metadata = response.result.usage_metadata
                     usage.input_tokens = getattr(metadata, 'prompt_token_count', 0)
                     usage.output_tokens = getattr(metadata, 'candidates_token_count', 0)
                     usage.total_tokens = getattr(metadata, 'total_token_count', 0)
            
            return usage
        except Exception as e:
            print(f"Warning: Could not extract token usage: {e}")
            import traceback
            traceback.print_exc()
            return TokenUsage()
    
    def extract_from_page(
        self, 
        image: Image.Image, 
        page_num: int, 
        previous_items: List[str] = None
    ) -> Tuple[PageWiseLineItem, TokenUsage]:
        """
        Extract bill items from a single page
        """
        # Get appropriate prompt
        prompt = get_extraction_prompt(page_num, previous_items)
        
        # Create message with image
        try:
            response = self.model.generate_content(
                [prompt, image],
                safety_settings={
                    'HATE': 'BLOCK_NONE',
                    'HARASSMENT': 'BLOCK_NONE',
                    'SEXUAL': 'BLOCK_NONE',
                    'DANGEROUS': 'BLOCK_NONE'
                }
            )
            
            # Update token usage
            token_usage = self._update_token_usage(response)
            self.total_token_usage.add(token_usage)
            
            # Parse response
            response_text = response.text
            data = self._extract_json_from_response(response_text)
            
            # Validate and create PageWiseLineItem
            page_type = data.get('page_type', 'Bill Detail')
            bill_items_data = data.get('bill_items', [])
            
            # Convert to BillItem objects
            bill_items = []
            for item_data in bill_items_data:
                try:
                    bill_item = BillItem(
                        item_name=item_data.get('item_name', 'Unknown'),
                        item_amount=float(item_data.get('item_amount', 0.0)),
                        item_rate=float(item_data.get('item_rate', 0.0)),
                        item_quantity=float(item_data.get('item_quantity', 1.0))
                    )
                    bill_items.append(bill_item)
                except Exception as e:
                    print(f"Warning: Skipping invalid item: {item_data}. Error: {e}")
            
            page_item = PageWiseLineItem(
                page_no=str(page_num),
                page_type=page_type,
                bill_items=bill_items
            )
            
            return page_item, token_usage
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract from page {page_num}: {str(e)}")
    
    def extract_from_pages(
        self, 
        images: List[Image.Image]
    ) -> Tuple[List[PageWiseLineItem], TokenUsage]:
        """
        Extract bill items from multiple pages
        """
        all_page_items = []
        previous_items = []
        
        for i, image in enumerate(images):
            page_num = i + 1
            
            try:
                # Extract from this page
                page_item, token_usage = self.extract_from_page(
                    image, 
                    page_num, 
                    previous_items if page_num > 1 else None
                )
                
                all_page_items.append(page_item)
                
                # Update previous items list
                for item in page_item.bill_items:
                    previous_items.append(item.item_name)
                
                # Small delay to avoid rate limiting
                if i < len(images) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
                # Continue with next page
                continue
        
        return all_page_items, self.total_token_usage

    def _pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Convert PDF bytes to list of PIL Images (one per page)
        """
        import io
        import pypdf
        
        images = []
        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        
        print(f"Converting PDF with {len(pdf_reader.pages)} pages to images...")
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                # Get page dimensions
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Calculate scale for good resolution (300 DPI equivalent)
                scale = 2.0  # 2x scale for better quality
                width = int(page_width * scale)
                height = int(page_height * scale)
                
                # Create blank white image
                img = Image.new('RGB', (width, height), 'white')
                
                # Note: pypdf doesn't have built-in rendering, but we can use the page content
                # For production, consider using pdf2image library
                # For now, we'll rely on Gemini's PDF processing with fallback
                
                print(f"Warning: PDF to image conversion is limited. Page {page_num} may not render perfectly.")
                images.append(img)
                
            except Exception as e:
                print(f"Warning: Could not convert page {page_num}: {e}")
                continue
        
        return images

    def _should_chunk_pdf(self, page_count: int) -> bool:
        """Determine if PDF should be chunked based on page count"""
        # Chunk if more than 8 pages to avoid token limits
        return page_count > 8

    def extract_from_document(
        self, 
        content: Any, 
        mime_type: str = "application/pdf"
    ) -> Tuple[List[PageWiseLineItem], TokenUsage]:
        """
        Extract bill items from a document using Gemini Vision API directly
        Automatically chunks large PDFs to avoid token limits
        """
        try:
            # Step 1: Handle PDF
            if mime_type == "application/pdf":
                # Get PDF bytes
                if isinstance(content, bytes):
                    pdf_bytes = content
                else:
                    pdf_bytes = content.read() if hasattr(content, 'read') else content
                
                # Get page count to determine strategy
                import io
                import pypdf
                pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                page_count = len(pdf_reader.pages)
                
                print(f"\nPDF has {page_count} page(s)")
                
                # Strategy: Try direct upload first, fallback to chunking if needed
                if self._should_chunk_pdf(page_count):
                    print(f"Large PDF detected ({page_count} pages). Using chunked processing...")
                    return self._extract_pdf_chunked(pdf_bytes, page_count)
                else:
                    print(f"Processing PDF directly with Gemini...")
                    try:
                        return self._extract_pdf_direct(pdf_bytes)
                    except ValueError as e:
                        # Check if it's a truncation error
                        if "truncation" in str(e).lower() or "parse JSON" in str(e):
                            print(f"⚠️  Direct processing failed (likely truncation). Retrying with chunked processing...")
                            return self._extract_pdf_chunked(pdf_bytes, page_count)
                        else:
                            raise

            # Step 2: Handle Images (Page by Page)
            elif mime_type.startswith("image/"):
                print("Processing image with Gemini Vision...")
                
                if isinstance(content, Image.Image):
                    images = [content]
                else:
                    import io
                    images = [Image.open(io.BytesIO(content))]
                
                return self.extract_from_pages(images)
            
            else:
                raise ValueError(f"Unsupported mime type: {mime_type}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to extract from document: {str(e)}")

    def _extract_pdf_direct(self, pdf_bytes: bytes) -> Tuple[List[PageWiseLineItem], TokenUsage]:
        """Extract from PDF using direct Gemini File API upload"""
        print(f"\nUploading PDF to Gemini (Direct Processing)...")
        
        # Save PDF to temp file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        
        try:
            # Upload to Gemini
            print("Uploading file to Gemini...")
            file_ref = genai.upload_file(tmp_path, mime_type="application/pdf")
            print(f"File uploaded: {file_ref.name}")
            
            # Wait for processing state
            while file_ref.state.name == "PROCESSING":
                print("Processing file...", end="\r")
                time.sleep(1)
                file_ref = genai.get_file(file_ref.name)
            
            if file_ref.state.name == "FAILED":
                raise ValueError("Gemini failed to process the PDF file")
                
            print("\nFile processed successfully. Extracting data...")
            
            # Generate content with full document prompt
            response = self.model.generate_content(
                [FULL_DOCUMENT_PROMPT, file_ref],
                safety_settings={
                    'HATE': 'BLOCK_NONE',
                    'HARASSMENT': 'BLOCK_NONE',
                    'SEXUAL': 'BLOCK_NONE',
                    'DANGEROUS': 'BLOCK_NONE'
                }
            )
            
            # Check if response was truncated
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = response.candidates[0].finish_reason
                if finish_reason == 2:  # RECITATION or MAX_TOKENS
                    raise ValueError("Response truncated due to token limits")
            
            # Process response
            return self._process_gemini_response(response)
            
        finally:
            # Clean up local temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _extract_pdf_chunked(self, pdf_bytes: bytes, page_count: int) -> Tuple[List[PageWiseLineItem], TokenUsage]:
        """
        Extract from large PDF by processing pages in chunks
        Uses Gemini File API to upload each page range separately
        """
        import io
        import pypdf
        
        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        all_page_items = []
        previous_items = []
        
        # Process in chunks of 3 pages
        chunk_size = 3
        total_chunks = (page_count + chunk_size - 1) // chunk_size
        
        print(f"Processing {page_count} pages in {total_chunks} chunks of {chunk_size} pages each...")
        
        for chunk_idx in range(total_chunks):
            start_page = chunk_idx * chunk_size
            end_page = min(start_page + chunk_size, page_count)
            
            print(f"\n📄 Processing chunk {chunk_idx + 1}/{total_chunks} (pages {start_page + 1}-{end_page})...")
            
            # Create a new PDF with just this chunk
            chunk_pdf = pypdf.PdfWriter()
            for page_num in range(start_page, end_page):
                chunk_pdf.add_page(pdf_reader.pages[page_num])
            
            # Save chunk to bytes
            chunk_io = io.BytesIO()
            chunk_pdf.write(chunk_io)
            chunk_bytes = chunk_io.getvalue()
            
            # Process this chunk
            try:
                chunk_items, _ = self._extract_pdf_direct(chunk_bytes)
                
                # Adjust page numbers to match original document
                for item in chunk_items:
                    original_page_no = int(item.page_no) + start_page
                    item.page_no = str(original_page_no)
                
                all_page_items.extend(chunk_items)
                
                # Update previous items for context
                for page_item in chunk_items:
                    for bill_item in page_item.bill_items:
                        previous_items.append(bill_item.item_name)
                
                # Small delay between chunks to avoid rate limits
                if chunk_idx < total_chunks - 1:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"⚠️  Error processing chunk {chunk_idx + 1}: {e}")
                # Continue with next chunk
                continue
        
        print(f"\n✅ Completed chunked processing: {len(all_page_items)} pages extracted")
        return all_page_items, self.total_token_usage

    def _process_gemini_response(self, response) -> Tuple[List[PageWiseLineItem], TokenUsage]:
        """Helper to process Gemini response into structured data"""
        # Update token usage
        token_usage = self._update_token_usage(response)
        self.total_token_usage.add(token_usage)
        
        print(f"Debug: Response finish reason: {response.candidates[0].finish_reason if response.candidates else 'None'}")
        
        # Parse response
        try:
            print(f"Debug: Raw response text: {response.text[:500]}...")
            response_text = response.text
        except Exception as e:
            print(f"Debug: Failed to get response.text: {e}")
            if response.candidates and response.candidates[0].content.parts:
                response_text = response.candidates[0].content.parts[0].text
                print(f"Debug: Got text from parts: {response_text[:500]}...")
            else:
                print("Debug: No content in response candidates")
                return [], self.total_token_usage

        data = self._extract_json_from_response(response_text)
        
        # Print LLM output for verification
        print("\n" + "="*80)
        print("🤖 GEMINI VISION OUTPUT:")
        print("="*80)
        print(json.dumps(data, indent=2)[:2000])
        if len(json.dumps(data, indent=2)) > 2000:
            print("\n... (showing first 2000 characters)")
        print("="*80 + "\n")
        
        # Convert to PageWiseLineItem objects
        all_page_items = []
        pagewise_data = data.get('pagewise_line_items', [])
        
        # Handle case where model returns single object instead of list
        if isinstance(pagewise_data, dict):
            pagewise_data = [pagewise_data]
            
        # If model returned flat list of items (fallback), wrap in single page
        if not pagewise_data and 'bill_items' in data:
            pagewise_data = [{
                'page_no': '1',
                'page_type': 'Bill Detail',
                'bill_items': data['bill_items']
            }]
        
        for page_data in pagewise_data:
            try:
                # Convert bill items
                bill_items = []
                for item_data in page_data.get('bill_items', []):
                    try:
                        bill_item = BillItem(
                            item_name=item_data.get('item_name', 'Unknown'),
                            item_amount=float(item_data.get('item_amount', 0.0)),
                            item_rate=float(item_data.get('item_rate', 0.0)),
                            item_quantity=float(item_data.get('item_quantity', 1.0))
                        )
                        bill_items.append(bill_item)
                    except Exception as e:
                        print(f"Warning: Skipping invalid item: {item_data}. Error: {e}")
                
                page_item = PageWiseLineItem(
                    page_no=str(page_data.get('page_no', '1')),
                    page_type=page_data.get('page_type', 'Bill Detail'),
                    bill_items=bill_items
                )
                all_page_items.append(page_item)
            except Exception as e:
                print(f"Error processing page data: {e}")
                continue
        
        return all_page_items, self.total_token_usage
    
    def get_token_usage(self) -> TokenUsage:
        """Get total token usage"""
        return self.total_token_usage
    
    def reset_token_usage(self):
        """Reset token usage counter"""
        self.total_token_usage = TokenUsage()
