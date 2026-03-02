from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import ValidationError

from config import SourceEnum, PortalEnum, ActionTypeEnum
from models.schemas import (
    ScrapeRequestSchema,
    ScrapeResponseSchema,
    ReportResponseSchema,
    TrackResponseSchema,
)
from portals.services.complaint_scraper import fetch_complaint_status
from portals.services.bbmp_complaint import raise_complaint

scrape_bp = Blueprint(
    "scrape",
    __name__,
    url_prefix="/api/v1/scrape",
    description="Scrape integration endpoints"
)


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
