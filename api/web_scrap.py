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
    description="BBMP Complaint Portal - Government Issue Portal Integration API"
)


# ----------------------------
# Endpoint
# ---------------------------- 
@scrape_bp.route("")
class ScrapeAPI(MethodView):
    """
    Scrape API Endpoint
    
    POST /api/v1/scrape
    
    Used for interacting with the BBMP (Bruhat Bengaluru Mahanagara Palike) 
    SmartOne Bangalore complaint portal to:
    - Report new issues/complaints
    - Track existing complaint status
    """

    @scrape_bp.arguments(ScrapeRequestSchema)
    @scrape_bp.response(200, ScrapeResponseSchema)
    def post(self, request_data):
        """
        Submit a scrape request
        
        ---
        Request Body:
            source (str): Source type - use "GOV_ISSUE_PORTAL"
            context (object): Request context containing:
                - portal: Portal identifier (e.g., "SMARTONEBLR")
                - action: Action to perform with type and data
                - auth: Authentication credentials
        
        Supported Actions:
            - REPORT_ISSUE: Submit a new complaint
            - TRACK_ISSUE: Check status of existing complaint
        
        Example (Report Issue):
            {
                "source": "GOV_ISSUE_PORTAL",
                "context": {
                    "portal": "SMARTONEBLR",
                    "action": {
                        "type": "REPORT_ISSUE",
                        "data": {
                            "category": "Road Engineering",
                            "sub_category": "Potholes",
                            "description": "Pothole on main road",
                            "media_url": "path/to/image.jpg",
                            "latitude": "12.9716",
                            "longitude": "77.5946"
                        }
                    },
                    "auth": {
                        "username": "user123",
                        "password": "pass123"
                    }
                }
            }
        
        Returns:
            200: Success - returns tracking_id
            400: Validation error
            500: Internal server error
        """

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
