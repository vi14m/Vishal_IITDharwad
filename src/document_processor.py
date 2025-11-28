"""
Document processing utilities for downloading and converting documents
"""
import io
import os
import tempfile
from typing import List, Tuple, Any
import requests
from PIL import Image
import base64
import pypdf


class DocumentProcessor:
    """Handle document download and conversion"""
    
    def __init__(self, timeout: int = 120):
        self.timeout = timeout
    
    def download_document(self, url: str) -> bytes:
        """Download document from URL"""
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to download document: {str(e)}")
    
    def is_pdf(self, content: bytes) -> bool:
        """Check if content is a PDF"""
        return content.startswith(b'%PDF')
    
    def is_image(self, content: bytes) -> bool:
        """Check if content is an image"""
        try:
            Image.open(io.BytesIO(content))
            return True
        except:
            return False
    
    def process_document(self, url: str) -> Tuple[List[Image.Image], int]:
        """
        Download and process document into images
        
        Returns:
            Tuple of (content, mime_type, page_count)
        """
        # Download document
        content = self.download_document(url)
        return self.process_file_content(content)

    def process_file_content(self, content: bytes) -> Tuple[Any, str, int]:
        """
        Process raw file content
        
        Args:
            content: Raw bytes of the file (PDF or image)
            
        Returns:
            Tuple of (content, mime_type, page_count)
            - content: bytes for PDF, PIL.Image for image
            - mime_type: "application/pdf" or "image/png"
            - page_count: number of pages
        """
        
        # Determine document type and process
        if self.is_pdf(content):
            # Get page count using pypdf
            try:
                pdf_reader = pypdf.PdfReader(io.BytesIO(content))
                page_count = len(pdf_reader.pages)
            except Exception:
                page_count = 1  # Fallback
                
            return content, "application/pdf", page_count
            
        elif self.is_image(content):
            image = Image.open(io.BytesIO(content))
            return image, "image/png", 1
        else:
            raise ValueError("Unsupported document format. Only PDF and images are supported.")
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def save_image_temp(self, image: Image.Image, prefix: str = "bill_page_") -> str:
        """Save image to temporary file and return path"""
        with tempfile.NamedTemporaryFile(
            mode='wb', 
            suffix='.png', 
            prefix=prefix,
            delete=False
        ) as tmp_file:
            image.save(tmp_file, format='PNG')
            return tmp_file.name
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """Remove temporary files"""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Warning: Failed to remove temp file {path}: {e}")
