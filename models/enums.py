# models/enums.py
"""
Centralized enumeration definitions for the web scraper application.
"""
from enum import Enum


class SourceEnum(str, Enum):
    """Data sources supported by the application."""
    GOV_ISSUE_PORTAL = "GOV_ISSUE_PORTAL"


class PortalEnum(str, Enum):
    """Portal identifiers for different complaint systems."""
    SMARTONEBLR = "SMARTONEBLR"


class ActionTypeEnum(str, Enum):
    """Action types for complaint operations."""
    REPORT_ISSUE = "REPORT_ISSUE"
    TRACK_ISSUE = "TRACK_ISSUE"


class ComplaintStatusEnum(str, Enum):
    """Status states for tracked complaints."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"
