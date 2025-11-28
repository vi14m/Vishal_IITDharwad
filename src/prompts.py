"""
Prompt templates for bill extraction using LLM
"""

SYSTEM_PROMPT = """You are an expert medical bill analyzer. Your task is to extract line item details from medical bills/invoices with perfect accuracy.

CRITICAL RULES:
1. Extract EVERY line item - missing items will cause errors
2. NEVER duplicate items across pages
3. Extract item_name EXACTLY as written in the bill
4. For item_amount: use the NET amount AFTER any discounts
5. Extract item_rate and item_quantity exactly as shown
6. If quantity is not shown, use 1.0
7. Ignore summary rows, sub-totals, and grand totals (extract only individual items)
8. DO NOT confuse dates, invoice numbers, or IDs with monetary amounts.
9. Verify that item_amount is actually a price/cost, not a code.

OUTPUT FORMAT: Return ONLY valid JSON, no markdown, no explanations."""

EXTRACTION_PROMPT = """Analyze this medical bill page and extract ALL line items.

For each line item, provide:
- item_name: exact name from the bill
- item_amount: net amount (after discounts if any)
- item_rate: rate per unit
- item_quantity: quantity

Also classify the page type as one of:
- "Bill Detail" - detailed charge breakdown
- "Final Bill" - summary/final bill page
- "Pharmacy" - pharmacy/medicine charges

Return JSON in this format:
{{
  "page_type": "Bill Detail|Final Bill|Pharmacy",
  "bill_items": [
    {{
      "item_name": "exact item name",
      "item_amount": 0.0,
      "item_rate": 0.0,
      "item_quantity": 0.0
    }}
  ]
}}

IMPORTANT:
- Extract ONLY individual line items, NOT subtotals or totals
- If you see "Sub Total", "Grand Total", "Total Amount" etc., SKIP those rows
- Be very careful to extract ALL items and avoid duplicates
- Return ONLY the JSON, no other text"""

FULL_DOCUMENT_PROMPT = """Analyze this entire medical bill document (which may have multiple pages) and extract ALL line items from every page.

For each page, provide:
- page_no: page number (1-indexed)
- page_type: one of "Bill Detail", "Final Bill", "Pharmacy"
- bill_items: list of items on that page

Return JSON in this format:
{
  "pagewise_line_items": [
    {
      "page_no": "1",
      "page_type": "Bill Detail",
      "bill_items": [
        {
          "item_name": "exact item name",
          "item_amount": 0.0,
          "item_rate": 0.0,
          "item_quantity": 0.0
        }
      ]
    }
  ]
}

IMPORTANT:
- Process EVERY page in the document
- Extract ONLY individual line items, NOT subtotals or totals
- If you see "Sub Total", "Grand Total", "Total Amount" etc., SKIP those rows
- Be very careful to extract ALL items and avoid duplicates
- Return ONLY the JSON, no other text

GUARD RAILS:
- Identify numeric values that represent currency (look for currency symbols or column headers like "Amount", "Price", "Total").
- Differentiate between key identifiers (like dates, invoice numbers, phone numbers) and transactional values.
- DO NOT extract Invoice Date, Invoice Number, or Phone Numbers as item_amount.
- If a number looks like a date (e.g., 2023, 11/12) or ID, it is NOT an amount."""

MULTIPAGE_CONTEXT_PROMPT = """This is page {page_num} of a multi-page bill.

Previous pages contained these items:
{previous_items}

CRITICAL: DO NOT re-extract items from previous pages. Only extract NEW items on this page."""

VALIDATION_PROMPT = """Review the extracted items and verify:

1. Are all line items extracted? (Check for any missing items)
2. Are there any duplicate items?
3. Do the amounts match what's shown in the bill?

Extracted items:
{items}

If you find issues, provide corrections. Otherwise, confirm the extraction is accurate."""


def get_extraction_prompt(page_num: int = 1, previous_items: list = None) -> str:
    """Get extraction prompt with optional context for multi-page bills"""
    if page_num > 1 and previous_items:
        # Format previous items
        prev_items_str = "\n".join([f"- {item}" for item in previous_items])
        context = MULTIPAGE_CONTEXT_PROMPT.format(
            page_num=page_num,
            previous_items=prev_items_str
        )
        return f"{EXTRACTION_PROMPT}\n\n{context}"
    return EXTRACTION_PROMPT


def get_validation_prompt(items: list) -> str:
    """Get validation prompt for extracted items"""
    items_str = "\n".join([f"{i+1}. {item}" for i, item in enumerate(items)])
    return VALIDATION_PROMPT.format(items=items_str)


OCR_PROMPT = """Transcribe all text from this document exactly as it appears. 
Preserve the layout, table structure, and whitespace as much as possible. 
Do not summarize or extract specific fields yet, just provide the raw text content."""

TEXT_EXTRACTION_PROMPT = """Analyze the following text extracted from a medical bill and extract ALL line items.

Input Text:
{text}

For each page/section in the text, provide:
- page_no: inferred page number
- page_type: one of "Bill Detail", "Final Bill", "Pharmacy"
- bill_items: list of items

Return JSON in this format:
{{
  "pagewise_line_items": [
    {{
      "page_no": "1",
      "page_type": "Bill Detail",
      "bill_items": [
        {{
          "item_name": "exact item name",
          "item_amount": 0.0,
          "item_rate": 0.0,
          "item_quantity": 0.0
        }}
      ]
    }}
  ]
}}

IMPORTANT:
- Extract ONLY individual line items, NOT subtotals or totals
- If you see "Sub Total", "Grand Total", "Total Amount" etc., SKIP those rows
- Be very careful to extract ALL items and avoid duplicates
- Return ONLY the JSON, no other text

GUARD RAILS:
- Identify numeric values that represent currency (look for currency symbols or column headers like "Amount", "Price", "Total").
- Differentiate between key identifiers (like dates, invoice numbers, phone numbers) and transactional values.
- DO NOT extract Invoice Date, Invoice Number, or Phone Numbers as item_amount.
- If a number looks like a date (e.g., 2023, 11/12) or ID, it is NOT an amount."""
