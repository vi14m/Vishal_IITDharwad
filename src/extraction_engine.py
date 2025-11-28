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
            raise ValueError(f"Failed to parse JSON from response: {e}")
    
    def _update_token_usage(self, response) -> TokenUsage:
        """Extract token usage from Gemini response"""
        try:
            usage = TokenUsage()
            if hasattr(response, 'usage_metadata'):
                metadata = response.usage_metadata
                usage.input_tokens = getattr(metadata, 'prompt_token_count', 0)
                usage.output_tokens = getattr(metadata, 'candidates_token_count', 0)
                usage.total_tokens = getattr(metadata, 'total_token_count', 0)
                
                # If total not provided, calculate it
                if usage.total_tokens == 0:
                    usage.total_tokens = usage.input_tokens + usage.output_tokens
            
            return usage
        except Exception as e:
            print(f"Warning: Could not extract token usage: {e}")
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

    def extract_from_document(
        self, 
        content: Any, 
        mime_type: str = "application/pdf"
    ) -> Tuple[List[PageWiseLineItem], TokenUsage]:
        """
        Extract bill items from a document using Gemini Vision API directly
        Bypasses OCR and uses the model's vision capabilities
        """
        try:
            # Step 1: Handle PDF directly with Gemini (no local conversion needed)
            if mime_type == "application/pdf":
                print(f"\nStep 1: Uploading PDF to Gemini (Direct Processing)...")
                
                # Save PDF to temp file for upload
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    if isinstance(content, bytes):
                        tmp.write(content)
                    else:
                        tmp.write(content.read() if hasattr(content, 'read') else content)
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
                    
                    # Clean up file from Gemini (optional but good practice)
                    # genai.delete_file(file_ref.name)
                    
                finally:
                    # Clean up local temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                
                # Process response
                return self._process_gemini_response(response)

            # Step 2: Handle Images (Page by Page)
            elif mime_type.startswith("image/"):
                print("Processing image with Gemini Vision...")
                from src.document_processor import DocumentProcessor
                
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
