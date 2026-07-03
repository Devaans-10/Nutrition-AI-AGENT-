import os
import json
from flask import Flask
from config import Config
import database as db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure database is initialized
    try:
        # Check if database setup is needed. db.init_db() uses CREATE TABLE IF NOT EXISTS.
        db.init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")

    # Register custom jinja filter to load JSON strings inside templates
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value)
        except Exception:
            return {}

    # Register blueprints
    from routes.main import main_bp
    from routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    return app

app = create_app()

if __name__ == '__main__':
    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True)
