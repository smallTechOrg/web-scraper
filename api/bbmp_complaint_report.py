from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields
from portals.services.bbmp_complaint import raise_complaint

complaint_report_bp = Blueprint(
    "complaint report",
    __name__,
    url_prefix="/api/complaintreport",
    description="BBMP Complaint Report Operations"
)

class ComplaintReportRequestSchema(Schema):
    category = fields.String(required=True)
    subcategory = fields.String(required=True)
    description = fields.String(required=True)
    image_path = fields.String(required=True)
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
    use_other_location = fields.Boolean(required=True)

class ComplaintReportResponseSchema(Schema):
    success = fields.Boolean()
    complaint_id = fields.String(allow_none=True)
    timestamp = fields.String(allow_none=True)
    error = fields.String(allow_none=True)

@complaint_report_bp.route("/")
class ComplaintReport(MethodView):

    @complaint_report_bp.arguments(ComplaintReportRequestSchema)
    @complaint_report_bp.response(200, ComplaintReportResponseSchema)
    def post(self, args):
        success, result = raise_complaint(**args)

        if success:
            return {
                "success": True,
                "complaint_id": result["complaint_id"],
                "timestamp": result["timestamp"],
                "error": None
            }

        return {
            "success": False,
            "complaint_id": None,
            "timestamp": None,
            "error": result.get("error", "Unknown error")
        }