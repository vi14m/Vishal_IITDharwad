from pydantic import BaseModel, Field, validator
from typing import List, Optional


class DocumentRequest(BaseModel):
    """Request model for bill extraction"""
    document: str = Field(..., description="URL to the document image/PDF")
    
    @validator('document')
    def validate_document_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Document must be a valid URL')
        return v


class BillItem(BaseModel):
    """Individual line item in a bill"""
    item_name: str = Field(..., description="Name of the item exactly as mentioned in the bill")
    item_amount: float = Field(..., description="Net amount of the item post discounts")
    item_rate: float = Field(..., description="Rate per unit exactly as mentioned")
    item_quantity: float = Field(..., description="Quantity exactly as mentioned")


class PageWiseLineItem(BaseModel):
    """Line items grouped by page"""
    page_no: str = Field(..., description="Page number")
    page_type: str = Field(..., description="Type of page: Bill Detail, Final Bill, or Pharmacy")
    bill_items: List[BillItem] = Field(default_factory=list, description="List of bill items on this page")
    
    @validator('page_type')
    def validate_page_type(cls, v):
        valid_types = ["Bill Detail", "Final Bill", "Pharmacy"]
        if v not in valid_types:
            # Try to correct common variations
            v_lower = v.lower()
            if "pharmacy" in v_lower:
                return "Pharmacy"
            elif "final" in v_lower or "summary" in v_lower:
                return "Final Bill"
            else:
                return "Bill Detail"
        return v


class TokenUsage(BaseModel):
    """Token usage information"""
    total_tokens: int = Field(default=0, description="Total tokens used")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    
    def add(self, other: 'TokenUsage'):
        """Add another TokenUsage to this one"""
        self.total_tokens += other.total_tokens
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens


class ExtractionData(BaseModel):
    """Extracted bill data"""
    pagewise_line_items: List[PageWiseLineItem] = Field(default_factory=list)
    total_item_count: int = Field(default=0, description="Total count of items across all pages")


class ExtractionResponse(BaseModel):
    """API response model"""
    is_success: bool = Field(default=True)
    token_usage: TokenUsage
    data: ExtractionData


class ErrorResponse(BaseModel):
    """Error response model"""
    is_success: bool = Field(default=False)
    message: str = Field(..., description="Error message")
