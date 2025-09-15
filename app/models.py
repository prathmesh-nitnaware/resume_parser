from . import db
from datetime import datetime

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(150), nullable=False, unique=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    skills = db.Column(db.Text)
    date_uploaded = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Resume {self.filename}>'