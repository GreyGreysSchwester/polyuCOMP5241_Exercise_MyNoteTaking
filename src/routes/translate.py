from flask import Blueprint, jsonify, request

from src.services.translator import (
    SUPPORTED_LANGUAGES,
    TranslationError,
    translate_note,
)

translate_bp = Blueprint('translate', __name__)


@translate_bp.route('/translate', methods=['POST'])
def translate():
    """Translate a note's title/content into the requested language.

    Request body:
        { "title": str, "content": str, "target_language": str }

    Response on success (200) -- JSON straight from the model:
        { "detected_source_language": str, "target_language": str,
          "translated_title": str, "translated_content": str }
    """
    data = request.json or {}

    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    target_language = data.get('target_language') or ''

    if not title and not content:
        return jsonify({'error': 'Nothing to translate - the note is empty'}), 400

    if target_language not in SUPPORTED_LANGUAGES:
        return jsonify({
            'error': f'Unsupported target language: {target_language!r}',
            'supported': SUPPORTED_LANGUAGES,
        }), 400

    try:
        result = translate_note(title, content, target_language)
    except TranslationError as e:
        return jsonify({'error': str(e)}), 502

    return jsonify(result)
