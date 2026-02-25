# api/login.py

from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields
from portals.services.bbmp_login import login_user

login_bp = Blueprint(
    "login",
    __name__,
    url_prefix="/api/login",
    description="BBMP Login Operations"
)


class LoginRequestSchema(Schema):
    mobile = fields.String(required=True)
    password = fields.String(required=True)


class LoginResponseSchema(Schema):
    success = fields.Boolean()
    message = fields.String()


@login_bp.route("/")
class Login(MethodView):

    @login_bp.arguments(LoginRequestSchema)
    @login_bp.response(200, LoginResponseSchema)
    def post(self, args):
        success, message = login_user(
            args["mobile"],
            args["password"]
        )

        return {
            "success": success,
            "message": message
        }