"""
Test script to evaluate extraction accuracy on training samples
"""
import os
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_processor import DocumentProcessor
from src.extraction_engine import ExtractionEngine
from src.validator import Validator
from config import config


def evaluate_sample(file_path: str):
    """Evaluate extraction on a single sample"""
    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(file_path)}")
    print('='*60)
    
    try:
        # Read file content directly
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Initialize components
        doc_processor = DocumentProcessor()
        extraction_engine = ExtractionEngine()
        validator = Validator()
        
        # Process document
        content, mime_type, page_count = doc_processor.process_file_content(file_content)
        print(f"Pages: {page_count}")
        
        # Extract
        pagewise_items, token_usage = extraction_engine.extract_from_document(content, mime_type)
        
        # Validate
        validation_report = validator.validate_all(pagewise_items)
        
        # Results
        print(f"Items extracted: {validation_report['item_count']}")
        print(f"Total amount: ${validation_report['total_amount']:.2f}")
        print(f"Duplicates found: {len(validation_report['duplicates'])}")
        print(f"Tokens used: {token_usage.total_tokens}")
        
        if validation_report['warnings']:
            print("\nWarnings:")
            for warning in validation_report['warnings'][:5]:  # Show first 5
                print(f"  - {warning}")
        
        return {
            'file': os.path.basename(file_path),
            'page_count': page_count,
            'item_count': validation_report['item_count'],
            'total_amount': validation_report['total_amount'],
            'duplicates': len(validation_report['duplicates']),
            'tokens': token_usage.total_tokens,
            'success': True
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'file': os.path.basename(file_path),
            'success': False,
            'error': str(e)
        }


def main():
    """Run evaluation on all training samples"""
    training_dir = Path(__file__).parent.parent / "TRAINING_SAMPLES"
    
    if not training_dir.exists():
        print(f"Training directory not found: {training_dir}")
        return
    
    # Get all PDF files
    pdf_files = sorted(training_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} training samples")
    
    results = []
    for pdf_file in pdf_files:
        result = evaluate_sample(str(pdf_file))
        results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"Successful: {len(successful)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")
    
    if successful:
        total_items = sum(r['item_count'] for r in successful)
        total_tokens = sum(r['tokens'] for r in successful)
        avg_tokens = total_tokens / len(successful)
        
        print(f"\nTotal items extracted: {total_items}")
        print(f"Average tokens per document: {avg_tokens:.0f}")
    
    if failed:
        print("\nFailed files:")
        for r in failed:
            print(f"  - {r['file']}: {r.get('error', 'Unknown error')}")
    
    # Save results
    results_file = Path(__file__).parent.parent / "evaluation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
