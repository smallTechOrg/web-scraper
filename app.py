from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
from api.health import health_bp
from api.web_scrap import scrape_bp
from config import DEBUG

def create_app() -> Flask:
    
    app = Flask(__name__)

    # -- flask-smorest / OpenAPI configuration ---------------------------------
    # Auto-generated spec is served at /api/openapi.json.
    # Interactive Swagger UI is served at /api/docs.
    app.config.update(
        API_TITLE="Chat API",
        API_VERSION="v1",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/api",
        OPENAPI_SWAGGER_UI_PATH="/docs",
        OPENAPI_SWAGGER_UI_URL="https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    )

    # -- Smorest-managed blueprints (auto-documented) --------------------------
    smorest_api = Api(app)
    smorest_api.register_blueprint(health_bp)
    smorest_api.register_blueprint(scrape_bp)

    CORS(app)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=DEBUG, port=5001)