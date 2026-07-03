# config.py 
import os
from dotenv import load_dotenv

# Re-export enums from models for backward compatibility
from models.enums import SourceEnum, PortalEnum, ActionTypeEnum

load_dotenv()
# Flask settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Groq LLM settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "meta-llama/llama-4-scout-17b-16e-instruct")

# Base URLs the caller is allowed to supply via the X-Backend-Url header (comma-separated).
# Staging and production share this scraper deployment, so the header lets each environment
# dedupe against its own database — but it must be restricted to known hosts to avoid SSRF.
ALLOWED_BACKEND_URLS = {
    url.strip().rstrip("/")
    for url in os.getenv("ALLOWED_BACKEND_URLS", "").split(",")
    if url.strip()
}
