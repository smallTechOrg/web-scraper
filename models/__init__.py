# models/__init__.py
"""
Models package for the web scraper application.
Provides centralized enums and schemas from api/web_scrap.py
"""
from models.enums import (
    SourceEnum,
    PortalEnum,
    ActionTypeEnum,
    ComplaintStatusEnum,
)

from models.schemas import (
    AuthSchema,
    ReportIssueDataSchema,
    TrackIssueDataSchema,
    ActionSchema,
    ContextSchema,
    ScrapeRequestSchema,
    ReportResponseSchema,
    TrackMetaSchema,
    TrackResponseSchema,
    ScrapeResponseSchema,
)

__all__ = [
    # Enums
    "SourceEnum",
    "PortalEnum",
    "ActionTypeEnum",
    "ComplaintStatusEnum",
    # Schemas (from web_scrap.py)
    "AuthSchema",
    "ReportIssueDataSchema",
    "TrackIssueDataSchema",
    "ActionSchema",
    "ContextSchema",
    "ScrapeRequestSchema",
    "ReportResponseSchema",
    "TrackMetaSchema",
    "TrackResponseSchema",
    "ScrapeResponseSchema",
]
