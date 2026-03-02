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
from portals import action_registry

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

        # Validate supported source
        if source != SourceEnum.GOV_ISSUE_PORTAL.value:
            raise ValidationError("Unsupported source")

        # Validate supported portal
        if portal != PortalEnum.SMARTONEBLR.value:
            raise ValidationError("Unsupported portal")

        # Validate action type is supported by checking if handler exists
        if not action_registry.is_registered(source, portal, action_type):
            raise ValidationError(
                f"Unsupported action type '{action_type}' for source '{source}' and portal '{portal}'"
            )

        # Dispatch to the appropriate handler
        try:
            success, result = action_registry.dispatch(
                source=source,
                portal=portal,
                action_type=action_type,
                action_data=action_data,
                context=context
            )
        except ValueError as e:
            raise ValidationError(str(e))

        if not success:
            error_message = result.get("error", "Unknown error")
            raise ValidationError(error_message)

        return result
