from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db
from src.models.attachment import Attachment

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Deleting a note removes its attachment rows as well.
    attachments = db.relationship(
        'Attachment',
        backref='note',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='Attachment.id',
    )

    def __repr__(self):
        return f'<Note {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'attachments': [a.to_dict() for a in self.attachments],
        }

