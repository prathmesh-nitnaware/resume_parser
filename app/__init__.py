from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resumes.db'
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

    db.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    with app.app_context():
        from .models import Resume
        db.create_all()

    return app
