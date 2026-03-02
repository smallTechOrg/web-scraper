from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields
from portals.services.complaint_scraper import fetch_complaint_status

complaint_bp = Blueprint(
    "complaint",
    __name__,
    url_prefix="/api",
    description="Complaint related operations"
)

class ComplaintQuerySchema(Schema):
    complaint_id = fields.String(required=True)

class ComplaintResponseSchema(Schema):
    success = fields.Boolean()
    complaint_id = fields.String()
    complaint_details = fields.Dict()
    staff_details = fields.Dict()
    error = fields.String(allow_none=True)

@complaint_bp.route("/complaint-status")
class ComplaintStatus(MethodView):

    @complaint_bp.arguments(ComplaintQuerySchema, location="query")
    @complaint_bp.response(200, ComplaintResponseSchema)
    def get(self, args):
        complaint_id = args["complaint_id"]
        return fetch_complaint_status(complaint_id)
