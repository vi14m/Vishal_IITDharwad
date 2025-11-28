"""
Groq API Integration for Bill Extraction
Fast, free LLM extraction using Groq API (Llama models)
"""
import json
import os
from typing import Dict, Any, Tuple
from groq import Groq
from src.models import PageWiseLineItem, BillItem, TokenUsage


class GroqExtractor:
    """Extract structured bill data using Groq API"""
    
    def __init__(self, api_key: str = None):
        """Initialize Groq client"""
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"  # Fast and accurate
        print(f"GroqExtractor initialized with model: {self.model}")
    
    def extract_bill_items(self, ocr_text: str) -> Tuple[list[PageWiseLineItem], TokenUsage]:
        """
        Extract bill line items from OCR text using Groq API
        
        Args:
            ocr_text: Text extracted from OCR
            
        Returns:
            Tuple of (list of PageWiseLineItem, TokenUsage)
        """
        try:
            print("\n" + "="*80)
            print("🤖 GROQ API - STARTING STRUCTURED EXTRACTION")
            print("="*80)
            
            # Create optimized prompt
            prompt = self._create_extraction_prompt(ocr_text)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert bill data extraction assistant. Extract line items accurately without missing or double-counting any entries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            # Extract token usage
            token_usage = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
            
            print(f"\n✅ GROQ EXTRACTION COMPLETE")
            print(f"💰 Tokens Used: {token_usage.total_tokens} (In: {token_usage.input_tokens}, Out: {token_usage.output_tokens})")
            
            # Parse response
            response_text = response.choices[0].message.content
            data = json.loads(response_text)
            
            # Print structured output for verification
            print("\n" + "="*80)
            print("📊 EXTRACTED STRUCTURED DATA:")
            print("="*80)
            print(json.dumps(data, indent=2)[:2000])
            if len(json.dumps(data, indent=2)) > 2000:
                print("\n... (showing first 2000 characters)")
            print("="*80 + "\n")
            
            # Convert to PageWiseLineItem objects
            pagewise_items = self._parse_response(data)
            
            return pagewise_items, token_usage
            
        except Exception as e:
            print(f"❌ Error in Groq extraction: {e}")
            import traceback
            traceback.print_exc()
            # Return empty result
            return [PageWiseLineItem(page_no="1", page_type="Bill Detail", bill_items=[])], TokenUsage()
    
    def _create_extraction_prompt(self, ocr_text: str) -> str:
        """Create optimized extraction prompt"""
        return f"""Extract all line items from this bill/invoice text. Follow these rules STRICTLY:

**CRITICAL RULES:**
1. Extract ONLY actual line items with prices/amounts (goods/services purchased)
2. DO NOT extract metadata like: Invoice Number, Date, Time, Customer ID, Tax ID, etc.
3. DO NOT double-count items (if an item appears on multiple pages, count it once)
4. Extract net amount AFTER discounts for each item
5. If quantity or rate is not mentioned, use 1.0 and item_amount respectively

**OCR Text:**
{ocr_text[:15000]}

**Required JSON Output Format:**
{{
  "pagewise_line_items": [
    {{
      "page_no": "1",
      "page_type": "Bill Detail | Final Bill | Pharmacy",
      "bill_items": [
        {{
          "item_name": "exact name from bill",
          "item_amount": 0.0,
          "item_rate": 0.0,
          "item_quantity": 1.0
        }}
      ]
    }}
  ]
}}

**Examples of what TO extract:**
- "Paracetamol Tablet - Rs 50" → item_name: "Paracetamol Tablet", item_amount: 50.0
- "Consultation Fee - Rs 500" → item_name: "Consultation Fee", item_amount: 500.0

**Examples of what NOT to extract:**
- Invoice Number: 12345
- Date: 2023-01-15
- Customer ID: CUST001

Return ONLY valid JSON, no other text."""

    def _parse_response(self, data: Dict[str, Any]) -> list[PageWiseLineItem]:
        """Parse JSON response into PageWiseLineItem objects"""
        pagewise_items = []
        
        pagewise_data = data.get('pagewise_line_items', [])
        
        # Handle single object instead of list
        if isinstance(pagewise_data, dict):
            pagewise_data = [pagewise_data]
        
        # Fallback if model returned flat structure
        if not pagewise_data and 'bill_items' in data:
            pagewise_data = [{
                'page_no': '1',
                'page_type': 'Bill Detail',
                'bill_items': data['bill_items']
            }]
        
        for page_data in pagewise_data:
            try:
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
                        print(f"⚠️  Warning: Skipping invalid item: {item_data}. Error: {e}")
                
                page_item = PageWiseLineItem(
                    page_no=str(page_data.get('page_no', '1')),
                    page_type=page_data.get('page_type', 'Bill Detail'),
                    bill_items=bill_items
                )
                pagewise_items.append(page_item)
            except Exception as e:
                print(f"⚠️  Error processing page data: {e}")
                continue
        
        return pagewise_items
