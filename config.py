# config.py 
import os
from dotenv import load_dotenv

# Re-export enums from models for backward compatibility
from models.enums import SourceEnum, PortalEnum, ActionTypeEnum

load_dotenv()
# Flask settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
