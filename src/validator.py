"""
Validation and aggregation utilities
"""
from typing import List, Dict, Set
from src.models import PageWiseLineItem, BillItem


class Validator:
    """Validate extracted bill data"""
    
    def __init__(self):
        self.detected_duplicates = []
        self.warnings = []
    
    def detect_duplicates(
        self, 
        pagewise_items: List[PageWiseLineItem]
    ) -> List[str]:
        """
        Detect potential duplicate items across pages
        
        Returns list of duplicate item names
        """
        seen_items = {}
        duplicates = []
        
        for page_item in pagewise_items:
            for bill_item in page_item.bill_items:
                item_key = (
                    bill_item.item_name.lower().strip(),
                    bill_item.item_amount,
                    bill_item.item_rate
                )
                
                if item_key in seen_items:
                    duplicates.append(bill_item.item_name)
                    self.warnings.append(
                        f"Potential duplicate: '{bill_item.item_name}' on page {page_item.page_no}"
                    )
                else:
                    seen_items[item_key] = page_item.page_no
        
        self.detected_duplicates = duplicates
        return duplicates
    
    def calculate_total(
        self, 
        pagewise_items: List[PageWiseLineItem]
    ) -> float:
        """
        Calculate total amount from all line items
        
        Returns sum of all item_amount values
        """
        total = 0.0
        for page_item in pagewise_items:
            for bill_item in page_item.bill_items:
                total += bill_item.item_amount
        return round(total, 2)
    
    def count_total_items(
        self, 
        pagewise_items: List[PageWiseLineItem]
    ) -> int:
        """Count total number of items across all pages"""
        count = 0
        for page_item in pagewise_items:
            count += len(page_item.bill_items)
        return count
    
    def validate_item(self, item: BillItem) -> List[str]:
        """
        Validate a single bill item
        
        Returns list of validation errors (empty if valid)
        """
        errors = []
        
        if not item.item_name or item.item_name.strip() == "":
            errors.append("Item name is empty")
        
        if item.item_amount < 0:
            errors.append(f"Invalid item_amount: {item.item_amount} (must be >= 0)")
        
        if item.item_rate < 0:
            errors.append(f"Invalid item_rate: {item.item_rate} (must be >= 0)")
        
        if item.item_quantity <= 0:
            errors.append(f"Invalid item_quantity: {item.item_quantity} (must be > 0)")
        
        # Check if amount roughly equals rate * quantity (allow 5% tolerance for rounding)
        expected_amount = item.item_rate * item.item_quantity
        if expected_amount > 0:
            diff_percent = abs(item.item_amount - expected_amount) / expected_amount
            if diff_percent > 0.05:  # More than 5% difference
                self.warnings.append(
                    f"Amount mismatch for '{item.item_name}': "
                    f"{item.item_amount} != {item.item_rate} × {item.item_quantity} "
                    f"(expected ~{expected_amount:.2f})"
                )
        
        return errors
    
    def validate_all(
        self, 
        pagewise_items: List[PageWiseLineItem]
    ) -> Dict[str, any]:
        """
        Validate all extracted data
        
        Returns validation report
        """
        self.warnings = []
        errors = []
        
        # Validate each item
        for page_item in pagewise_items:
            for bill_item in page_item.bill_items:
                item_errors = self.validate_item(bill_item)
                errors.extend(item_errors)
        
        # Detect duplicates
        duplicates = self.detect_duplicates(pagewise_items)
        
        # Calculate total
        total = self.calculate_total(pagewise_items)
        
        # Count items
        item_count = self.count_total_items(pagewise_items)
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": self.warnings,
            "duplicates": duplicates,
            "total_amount": total,
            "item_count": item_count
        }
    
    def remove_duplicates(
        self, 
        pagewise_items: List[PageWiseLineItem]
    ) -> List[PageWiseLineItem]:
        """
        Remove duplicate items, keeping first occurrence
        
        Returns cleaned list
        """
        seen_items = set()
        cleaned_pages = []
        
        for page_item in pagewise_items:
            cleaned_items = []
            
            for bill_item in page_item.bill_items:
                item_key = (
                    bill_item.item_name.lower().strip(),
                    bill_item.item_amount,
                    bill_item.item_rate
                )
                
                if item_key not in seen_items:
                    cleaned_items.append(bill_item)
                    seen_items.add(item_key)
            
            # Only include page if it has items
            if cleaned_items:
                page_item.bill_items = cleaned_items
                cleaned_pages.append(page_item)
        
        return cleaned_pages
