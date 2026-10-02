from flask import Blueprint, jsonify, request

from src.models.attachment import Attachment
from src.models.note import Note
from src.models.user import db
from src.services import storage

attachment_bp = Blueprint('attachment', __name__)


@attachment_bp.route('/notes/<int:note_id>/attachments', methods=['GET'])
def list_attachments(note_id):
    """List the files attached to a note."""
    Note.query.get_or_404(note_id)
    items = Attachment.query.filter_by(note_id=note_id).order_by(Attachment.id).all()
    return jsonify([a.to_dict() for a in items])


@attachment_bp.route('/notes/<int:note_id>/attachments', methods=['POST'])
def upload_attachment(note_id):
    """Upload a file and attach it to the note.

    Expects multipart/form-data with a single ``file`` field. The file is
    forwarded to Supabase Storage; only its metadata is kept in the database.
    """
    Note.query.get_or_404(note_id)

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    data = file.read()

    try:
        stored = storage.upload(data, file.filename, file.mimetype, note_id)
    except storage.StorageError as e:
        return jsonify({'error': str(e)}), 400

    attachment = Attachment(
        note_id=note_id,
        filename=file.filename,
        storage_path=stored['storage_path'],
        url=stored['url'],
        mimetype=file.mimetype,
        size=len(data),
    )
    db.session.add(attachment)
    db.session.commit()

    return jsonify(attachment.to_dict()), 201


@attachment_bp.route('/attachments/<int:attachment_id>', methods=['DELETE'])
def delete_attachment(attachment_id):
    """Detach a file: remove it from the bucket and drop the database row."""
    attachment = Attachment.query.get_or_404(attachment_id)

    try:
        storage.delete(attachment.storage_path)
    except storage.StorageError:
        # The object may already be gone; the row should still be removed so
        # the UI does not keep showing a dead link.
        pass

    db.session.delete(attachment)
    db.session.commit()
    return '', 204
