# models/schemas.py
"""
Centralized Marshmallow schema definitions for the web scraper application.
Contains schemas from api/web_scrap.py

API Contract:
    POST /api/v1/scrape
    
    Request:
    {
        "source": "GOV_ISSUE_PORTAL",
        "context": {
            "portal": "SMARTONEBLR",
            "action": {
                "type": "REPORT_ISSUE",
                "data": {
                    "category": "Road Engineering",
                    "sub_category": "laptop",
                    "description": "optional_id",
                    "media_url": "optional_id",
                    "latitude": "optional_id",
                    "longitude": "optional_id"
                }
            },
            "auth": {
                "username": "user123",
                "password": "pass123"
            }
        }
    }
    
    Response (Report Issue):
    {
        "data": {
            "tracking_id": 21025835
        }
    }
"""
from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from models.enums import SourceEnum, PortalEnum, ActionTypeEnum, ComplaintStatusEnum


# ----------------------------
# Authentication Schemas
# ----------------------------

class AuthSchema(Schema):
    """Schema for authentication credentials."""
    username = fields.String(required=True, metadata={
        "description": "Username for portal authentication",
        "example": "user123"
    })
    password = fields.String(required=True, load_only=True, metadata={
        "description": "Password for portal authentication",
        "example": "pass123"
    })


# ----------------------------
# Action Data Schemas
# ----------------------------

class ReportIssueDataSchema(Schema):
    """Schema for reporting a new issue data."""
    category = fields.String(required=True, metadata={
        "description": "Main category of the issue (e.g., Road Engineering)",
        "example": "Road Engineering"
    })
    sub_category = fields.String(required=True, metadata={
        "description": "Sub-category of the issue (e.g., Potholes, Streetlight)",
        "example": "Potholes"
    })
    description = fields.String(required=False, metadata={
        "description": "Detailed description of the issue",
        "example": "Large pothole on the main road near the bus stop"
    })
    media_url = fields.String(required=False, metadata={
        "description": "Path to image file showing the issue",
        "example": "path/to/image.jpg"
    })
    latitude = fields.String(required=False, metadata={
        "description": "Latitude coordinate of the issue location",
        "example": "12.9716"
    })
    longitude = fields.String(required=False, metadata={
        "description": "Longitude coordinate of the issue location",
        "example": "77.5946"
    })


class TrackIssueDataSchema(Schema):
    """Schema for tracking an existing issue."""
    tracking_id = fields.String(required=True, metadata={
        "description": "The tracking ID of the complaint to track",
        "example": "21025835"
    })


# ----------------------------
# Action Schemas
# ----------------------------

class ActionSchema(Schema):
    """Schema for action configuration."""
    type = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in ActionTypeEnum]),
        metadata={
            "description": "Type of action to perform",
            "example": "REPORT_ISSUE",
            "enum": [e.value for e in ActionTypeEnum]
        }
    )
    data = fields.Dict(required=True, metadata={
        "description": "Action-specific data payload"
    })


class ContextSchema(Schema):
    """Schema for portal context with action and auth."""
    portal = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in PortalEnum]),
        metadata={
            "description": "Portal identifier",
            "example": "SMARTONEBLR",
            "enum": [e.value for e in PortalEnum]
        }
    )
    action = fields.Nested(ActionSchema, required=True, metadata={
        "description": "Action to perform on the portal"
    })
    auth = fields.Nested(AuthSchema, required=True, metadata={
        "description": "Authentication credentials for the portal"
    })


# ----------------------------
# Request Schemas
# ----------------------------

class ScrapeRequestSchema(Schema):
    """
    Main request schema for scrape operations.
    
    This is the root schema for the POST /api/v1/scrape endpoint.
    """
    source = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in SourceEnum]),
        metadata={
            "description": "Source type for the scrape operation",
            "example": "GOV_ISSUE_PORTAL",
            "enum": [e.value for e in SourceEnum]
        }
    )
    context = fields.Nested(ContextSchema, required=True, metadata={
        "description": "Context containing portal, action, and authentication"
    })

    @validates_schema
    def validate_action_data(self, data, **kwargs):
        action = data["context"]["action"]
        action_type = action["type"]
        action_data = action["data"]

        if action_type == ActionTypeEnum.REPORT_ISSUE.value:
            errors = ReportIssueDataSchema().validate(action_data)
        elif action_type == ActionTypeEnum.TRACK_ISSUE.value:
            errors = TrackIssueDataSchema().validate(action_data)
        elif action_type == ActionTypeEnum.FETCH_EVENTS.value:
            errors = TrackIssueDataSchema().validate(action_data)
        else:
            errors = {"type": ["Invalid action type"]}

        if errors:
            raise ValidationError({"context": {"action": {"data": errors}}})


# ----------------------------
# Response Schemas
# ----------------------------

class ReportResponseSchema(Schema):
    """Schema for report response - returns tracking_id after complaint submission."""
    tracking_id = fields.Integer(required=True, metadata={
        "description": "Unique tracking ID for the submitted complaint",
        "example": 232
    })


class TrackMetaSchema(Schema):
    """Schema for tracking metadata - contains staff info and remarks."""
    remarks = fields.String(required=False, allow_none=True, metadata={
        "description": "Any remarks on the complaint",
        "example": "Issue resolved"
    })
    staff_name = fields.String(required=False, allow_none=True, metadata={
        "description": "Name of staff handling the complaint",
        "example": "John Doe"
    })
    mobile_number = fields.Integer(required=False, allow_none=True, metadata={
        "description": "Contact number of the staff",
        "example": 1234567890
    })


class TrackResponseSchema(Schema):
    """Schema for tracking response - returns status and metadata."""
    status = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in ComplaintStatusEnum]),
        metadata={
            "description": "Current status of the complaint",
            "example": "CLOSED",
            "enum": [e.value for e in ComplaintStatusEnum]
        }
    )
    meta_data = fields.Nested(TrackMetaSchema, required=False, allow_none=True, metadata={
        "description": "Additional metadata about the complaint (staff info, remarks)"
    })


class ScrapeResponseSchema(Schema):
    """Schema for scrape response wrapper."""
    data = fields.Raw(required=True, metadata={
        "description": "Response data payload (varies by action type)"
    })
