import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate # Import Flask-Migrate

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate() # Initialize Migrate

def create_app():
    app = Flask(__name__)
    
    # Use environment variable for SECRET_KEY in production
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-very-secret-key-for-dev')
    
    # Use environment variable for PostgreSQL in production, fallback to SQLite for local dev
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///wms.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db) # Initialize Migrate with app and db

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    from wms.routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        from . import models
        # db.create_all() # No longer call create_all directly, use Flask-Migrate

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    return app