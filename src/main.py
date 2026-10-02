import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy.pool import NullPool
from src.models.user import db
from src.routes.user import user_bp
from src.routes.note import note_bp
from src.routes.translate import translate_bp
from src.routes.attachment import attachment_bp
from src.models.note import Note
from src.models.attachment import Attachment

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app)

# register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(note_bp, url_prefix='/api')
app.register_blueprint(translate_bp, url_prefix='/api')
app.register_blueprint(attachment_bp, url_prefix='/api')

# Reject oversized uploads before they are buffered in memory. Kept below
# Vercel's ~4.5 MB serverless request-body limit so local and deployed
# behaviour match.
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_MB', '4')) * 1024 * 1024


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({
        'error': f"File is too large. Maximum size is {os.getenv('MAX_UPLOAD_MB', '4')} MB."
    }), 413
# --- Configuration ----------------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Load .env during local development. On a deployment platform (e.g. Vercel)
# the variables are supplied by the platform and no .env file exists, in which
# case load_dotenv is a harmless no-op.
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# --- Database ---------------------------------------------------------------
# The app is stateless: serverless platforms (Vercel) wipe the local disk
# between requests, so a SQLite file cannot be relied on. All data lives in an
# external Postgres database (Supabase) instead.
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise RuntimeError(
        'DATABASE_URL is not set. Add it to .env for local development, or to '
        'the environment variables of your deployment platform.'
    )

# SQLAlchemy needs the driver named explicitly. Supabase hands out URLs that
# start with `postgres://` or `postgresql://`.
for prefix in ('postgres://', 'postgresql://'):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = 'postgresql+psycopg2://' + DATABASE_URL[len(prefix):]
        break

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Ping before use and recycle, so connections dropped by the pooler are
# detected instead of failing the request.
engine_options = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
if os.getenv('VERCEL'):
    # On serverless every invocation is short-lived and the process may be
    # frozen between requests, so holding pooled connections open is wasteful
    # and can exhaust the pooler. Vercel sets the VERCEL env var for us.
    engine_options['poolclass'] = NullPool
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    # Ignore third-party packages: lazily-imported libraries (e.g. openai
    # pulling in anyio on the first request) write __pycache__ files, which
    # would otherwise make the auto-reloader restart the server mid-request.
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        exclude_patterns=['*site-packages*', '*AppData*'],
    )
