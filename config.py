# Add other constants as needed
import os
from dotenv import load_dotenv

load_dotenv()
# Flask settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"