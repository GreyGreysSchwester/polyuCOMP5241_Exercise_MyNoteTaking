from datetime import datetime

from src.models.user import db


class Attachment(db.Model):
    """A file attached to a note.

    The file itself lives in Supabase Storage; this table only records where to
    find it. ``storage_path`` stays server-side (it is needed to delete the
    object), while ``url`` is the public link the browser uses.
    """

    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(512), nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    mimetype = db.Column(db.String(128))
    size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Attachment {self.filename}>'

    def to_dict(self):
        return {
            'id': self.id,
            'note_id': self.note_id,
            'filename': self.filename,
            'url': self.url,
            'mimetype': self.mimetype,
            'size': self.size,
            'is_image': bool(self.mimetype and self.mimetype.startswith('image/')),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
