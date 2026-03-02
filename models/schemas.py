# models/schemas.py
"""
Centralized Marshmallow schema definitions for the web scraper application.
Contains schemas from api/web_scrap.py
"""
from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from models.enums import SourceEnum, PortalEnum, ActionTypeEnum, ComplaintStatusEnum


# ----------------------------
# Authentication Schemas
# ----------------------------

class AuthSchema(Schema):
    """Schema for authentication credentials."""
    username = fields.String(required=True)
    password = fields.String(required=True)


# ----------------------------
# Action Data Schemas
# ----------------------------

class ReportIssueDataSchema(Schema):
    """Schema for reporting a new issue."""
    category = fields.String(required=True)
    sub_category = fields.String(required=True)
    description = fields.String(required=False)
    media_url = fields.String(required=False)
    latitude = fields.String(required=False)
    longitude = fields.String(required=False)


class TrackIssueDataSchema(Schema):
    """Schema for tracking an existing issue."""
    tracking_id = fields.String(required=True)


# ----------------------------
# Action Schemas
# ----------------------------

class ActionSchema(Schema):
    """Schema for action configuration."""
    type = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in ActionTypeEnum])
    )
    data = fields.Dict(required=True)


class ContextSchema(Schema):
    """Schema for portal context with action and auth."""
    portal = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in PortalEnum])
    )
    action = fields.Nested(ActionSchema, required=True)
    auth = fields.Nested(AuthSchema, required=True)


# ----------------------------
# Request Schemas
# ----------------------------

class ScrapeRequestSchema(Schema):
    """Main request schema for scrape operations."""
    source = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in SourceEnum])
    )
    context = fields.Nested(ContextSchema, required=True)

    @validates_schema
    def validate_action_data(self, data, **kwargs):
        action = data["context"]["action"]
        action_type = action["type"]
        action_data = action["data"]

        if action_type == ActionTypeEnum.REPORT_ISSUE.value:
            errors = ReportIssueDataSchema().validate(action_data)
        elif action_type == ActionTypeEnum.TRACK_ISSUE.value:
            errors = TrackIssueDataSchema().validate(action_data)
        else:
            errors = {"type": ["Invalid action type"]}

        if errors:
            raise ValidationError({"context": {"action": {"data": errors}}})


# ----------------------------
# Response Schemas
# ----------------------------

class ReportResponseSchema(Schema):
    """Schema for report response."""
    tracking_id = fields.Integer(required=True)


class TrackMetaSchema(Schema):
    """Schema for tracking metadata."""
    remarks = fields.String()
    staff_name = fields.String()
    mobile_number = fields.Integer()


class TrackResponseSchema(Schema):
    """Schema for tracking response."""
    status = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in ComplaintStatusEnum])
    )
    meta_data = fields.Nested(TrackMetaSchema)


class ScrapeResponseSchema(Schema):
    """Schema for scrape response."""
    data = fields.Raw(required=True)
