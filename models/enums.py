# models/enums.py
"""
Centralized enumeration definitions for the web scraper application.
"""
from enum import Enum


class SourceEnum(str, Enum):
    """Data sources supported by the application."""
    GOV_ISSUE_PORTAL = "GOV_ISSUE_PORTAL"
    EVENT_PORTAL = "EVENT_PORTAL" 


class PortalEnum(str, Enum):
    """Portal identifiers for different complaint systems."""
    SMARTONEBLR = "SMARTONEBLR"
    TEAMEVEREST = "TEAMEVEREST"
    MYBHARATGOVIN = "MYBHARATGOVIN"
    IVOLUNTEERIN = "IVOLUNTEERIN"


class ActionTypeEnum(str, Enum):
    """Action types for complaint operations."""
    REPORT_ISSUE = "REPORT_ISSUE"
    TRACK_ISSUE = "TRACK_ISSUE"
    FETCH_EVENTS = "FETCH_EVENTS"


class ComplaintStatusEnum(str, Enum):
    """Status states for tracked complaints."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class EventTypeEnum(str, Enum):
    """Event type categories for volunteering events."""
    CLEANLINESS_DRIVE = "CLEANLINESS_DRIVE"
    BEACH_CLEANUP = "BEACH_CLEANUP"
    ROAD_CLEANUP = "ROAD_CLEANUP"
    FOREST_CLEANUP = "FOREST_CLEANUP"
    TREEPLANTATION = "TREEPLANTATION"
    TREKANDPLOG = "TREKANDPLOG"
    VOLUNTEERING = "VOLUNTEERING"
    WORKSHOP = "WORKSHOP"
    OTHER = "OTHER"
