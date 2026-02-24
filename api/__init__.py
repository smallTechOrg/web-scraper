from .swagger import swaggerui_blueprint

def register_blueprints(app):
    app.register_blueprint(swaggerui_blueprint)
