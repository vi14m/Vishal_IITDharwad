"""
Configuration settings for the bill extraction API
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    
    # LLM Provider: 'gemini' (Vision) or 'groq' (Text)
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'gemini')
    
    # Server Configuration
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '8001'))
    

    GEMINI_MODEL = 'gemini-2.0-flash-lite' 
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.1'))
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '4096'))
    
    # Groq Model Configuration  
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
    
    # Processing Configuration
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 120  # seconds
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        # Always require Gemini key now as it's the primary engine
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for Gemini Vision extraction")
        return True

config = Config()
