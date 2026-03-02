# config.py 
import os
from dotenv import load_dotenv
from enum import Enum

load_dotenv()
# Flask settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"


class SourceEnum(str, Enum):
    GOV_ISSUE_PORTAL = "GOV_ISSUE_PORTAL"


class PortalEnum(str, Enum):
    SMARTONEBLR = "SMARTONEBLR"


class ActionTypeEnum(str, Enum):
    REPORT_ISSUE = "REPORT_ISSUE"
    TRACK_ISSUE = "TRACK_ISSUE"