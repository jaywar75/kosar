# kosar/app/__init__.py

import os
from flask import Flask, session
from .config import Config
from .extensions import mongo

# Import both blueprints
from .blueprints.main.routes import main_bp
from .blueprints.account.routes import account_bp

def create_app():
    # Figure out the path to this file and then the parent directory
    current_dir = os.path.abspath(os.path.dirname(__file__))  # e.g. .../kosar/app
    parent_dir = os.path.dirname(current_dir)                 # e.g. .../kosar

    # Construct the absolute path to ../static
    static_dir = os.path.join(parent_dir, "static")           # e.g. .../kosar/static

    # Override the default static folder so it points to the root-level 'static/'
    app = Flask(
        __name__,
        static_folder=static_dir,      # physically point to ../static
        static_url_path="/static"      # serve it at /static
    )

    # Load configurations
    app.config.from_object(Config)

    # Initialize MongoDB
    mongo.init_app(app)

    ####################################
    # Context Processor for Username
    ####################################
    @app.context_processor
    def inject_user():
        """
        Makes 'username' available in all templates if the user is logged in.
        """
        return dict(username=session.get('username'))

    # Register the main blueprint (handles "/")
    app.register_blueprint(main_bp)

    # Register the account blueprint (handles "/templates/...")
    app.register_blueprint(account_bp, url_prefix="/")

    return app