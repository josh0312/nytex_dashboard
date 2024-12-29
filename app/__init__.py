from flask import Flask
from flask_cors import CORS
from app.database import db
from app.config import Config
from app.logger import logger
from contextlib import contextmanager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    CORS(app)
    db.init_app(app)
    
    # Register blueprints
    from app.routes.dashboard import dashboard as dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    return app

@contextmanager
def app_context():
    app = create_app()
    with app.app_context():
        yield
