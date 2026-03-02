from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from config import SourceEnum, PortalEnum, ActionTypeEnum
from portals.services.complaint_scraper import fetch_complaint_status
from portals.services.bbmp_complaint import raise_complaint

scrape_bp = Blueprint(
    "scrape",
    __name__,
    url_prefix="/api/v1/scrape",
    description="Scrape integration endpoints"
)

# ----------------------------
# Common Nested Schemas
# ----------------------------

class AuthSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)


class ReportIssueDataSchema(Schema):
    category = fields.String(required=True)
    sub_category = fields.String(required=True)
    description = fields.String(required=False)
    media_url = fields.String(required=False)
    latitude = fields.String(required=False)
    longitude = fields.String(required=False)


class TrackIssueDataSchema(Schema):
    tracking_id = fields.String(required=True)

class ActionSchema(Schema):
    type = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in ActionTypeEnum])
    )
    data = fields.Dict(required=True)

class ContextSchema(Schema):
    portal = fields.String(
        required=True,
        validate=validate.OneOf([e.value for e in PortalEnum])
    )
    action = fields.Nested(ActionSchema, required=True)
    auth = fields.Nested(AuthSchema, required=True)


class ScrapeRequestSchema(Schema):
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

        if action_type == "REPORT_ISSUE":
            errors = ReportIssueDataSchema().validate(action_data)
        elif action_type == "TRACK_ISSUE":
            errors = TrackIssueDataSchema().validate(action_data)
        else:
            errors = {"type": ["Invalid action type"]}

        if errors:
            raise ValidationError({"context": {"action": {"data": errors}}})


# ----------------------------
# Response Schemas
# ----------------------------

class ReportResponseSchema(Schema):
    tracking_id = fields.Integer(required=True)


class TrackMetaSchema(Schema):
    remarks = fields.String()
    staff_name = fields.String()
    mobile_number = fields.Integer()


class TrackResponseSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(["OPEN", "IN_PROGRESS", "CLOSED"])
    )
    meta_data = fields.Nested(TrackMetaSchema)


class ScrapeResponseSchema(Schema):
    data = fields.Raw(required=True)


# ----------------------------
# Endpoint
# ---------------------------- 
@scrape_bp.route("/")
class ScrapeAPI(MethodView):

    @scrape_bp.arguments(ScrapeRequestSchema)
    @scrape_bp.response(200, ScrapeResponseSchema)
    def post(self, request_data):

        source = request_data["source"]
        context = request_data["context"]
        portal = context["portal"]
        action = context["action"]
        action_type = action["type"]
        action_data = action["data"]

        # Validate supported combination
        if source != SourceEnum.GOV_ISSUE_PORTAL.value:
            raise ValidationError("Unsupported source")

        if portal != PortalEnum.SMARTONEBLR.value:
            raise ValidationError("Unsupported portal")

        # -------------------------
        # TRACK ISSUE FLOW
        # -------------------------
        if action_type == ActionTypeEnum.TRACK_ISSUE.value:

            tracking_id = action_data["tracking_id"]

            result = fetch_complaint_status(tracking_id)

            if not result.get("success", False):
                raise ValidationError(result.get("error", "Failed to fetch complaint status"))

            return {
                "data": result
            }

        # -------------------------
        # REPORT ISSUE FLOW
        # -------------------------
        if action_type == ActionTypeEnum.REPORT_ISSUE.value:

            success, result = raise_complaint(
                category=action_data.get("category"),
                subcategory=action_data.get("sub_category"),
                description=action_data.get("description"),
                image_path=action_data.get("media_url"),
                latitude=action_data.get("latitude"),
                longitude=action_data.get("longitude"),
                use_other_location=False
            )

            if success:
                return {
                    "data": {
                        "tracking_id": result["complaint_id"]
                    }
                }

            raise ValidationError(
                result.get("error", "Failed to raise complaint")
            )

        raise ValidationError("Unsupported action type")