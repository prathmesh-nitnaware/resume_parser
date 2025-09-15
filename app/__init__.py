import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'a-very-secret-key-that-should-be-changed'),
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'resumes.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')

    try:
        os.makedirs(app.instance_path)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except OSError:
        pass

    db.init_app(app)

    from . import routes
    app.register_blueprint(routes.main)
    
    with app.app_context():
        from . import models
        db.create_all()

    return app