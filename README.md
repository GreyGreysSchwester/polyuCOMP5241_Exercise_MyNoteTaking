# NoteTaker - Personal Note Management Application

A modern, responsive web application for managing personal notes, with AI-powered
translation and file attachments.

## 🌟 Features

- **Create Notes**: Add new notes with titles and content
- **Edit Notes**: Update existing notes with debounced auto-save
- **Delete Notes**: Remove notes you no longer need
- **Search Notes**: Find notes quickly by searching titles and content
- **Translate Notes**: Translate a note into any of eight languages with one click
- **File Attachments**: Attach images and documents to a note, stored in object storage
- **Responsive Design**: Fluid layout that scales from phone to desktop
- **Modern UI**: Clean gradient design with smooth animations

## 🛠 Technology Stack

### Frontend
- **HTML5**: Semantic markup structure
- **CSS3**: Responsive styling built on `clamp()` and viewport units
- **JavaScript (ES6+)**: Interactive functionality and API communication

### Backend
- **Python Flask**: Web framework for API endpoints
- **SQLAlchemy**: ORM for database operations
- **Flask-CORS**: Cross-origin resource sharing support

### Database & Storage
- **PostgreSQL (Supabase)**: External database — the app itself is stateless
- **Supabase Storage**: Object storage for note attachments

### AI
- **OpenAI-compatible chat completions** (Gitee AI endpoint)
- Default model: `Qwen3-Coder-30B-A3B-Instruct` (configurable via `MODEL_NAME`)

## 📁 Project Structure

```
NoteTaker/
├── prompts/
│   └── translate_prompt.md    # Translation prompt template (placeholders filled at runtime)
├── src/
│   ├── models/
│   │   ├── user.py            # User model (template)
│   │   ├── note.py            # Note model, incl. its attachments relationship
│   │   └── attachment.py      # Attachment metadata model
│   ├── routes/
│   │   ├── user.py            # User API routes (template)
│   │   ├── note.py            # Note CRUD endpoints
│   │   ├── translate.py       # Translation endpoint
│   │   └── attachment.py      # Attachment upload/list/delete endpoints
│   ├── services/
│   │   ├── translator.py      # LLM client: prompt loading, API call, JSON parsing
│   │   └── storage.py         # Supabase Storage REST client
│   ├── static/
│   │   ├── index.html         # Single-page frontend (HTML + CSS + JS)
│   │   └── favicon.ico        # Application icon
│   └── main.py                # Flask application entry point
├── .env                       # Local secrets (git-ignored — never commit)
├── .env.example               # Template for the above
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🔧 Local Development Setup

### Prerequisites
- Python 3.11+
- pip (Python package manager)
- A PostgreSQL database (this project uses [Supabase](https://supabase.com))
- An API key for an OpenAI-compatible LLM endpoint (this project uses [Gitee AI](https://ai.gitee.com))

### Installation Steps

1. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
   On Windows: `venv\Scripts\activate`

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the environment**

   Copy the template and fill in your own credentials:
   ```bash
   cp .env.example .env
   ```

   | Variable | Purpose |
   |---|---|
   | `API_KEY` | API key for the LLM endpoint |
   | `BASE_URL` | OpenAI-compatible base URL, e.g. `https://ai.gitee.com/v1` |
   | `MODEL_NAME` | Model to use for translation |
   | `LLM_TIMEOUT` | Per-request timeout in seconds (default `90`) |
   | `DATABASE_URL` | PostgreSQL connection string |
   | `SUPABASE_URL` | Your Supabase project URL |
   | `SUPABASE_SERVICE_KEY` | Supabase **secret** key (`sb_secret_...`) — server-side only |
   | `SUPABASE_BUCKET` | Storage bucket name (default `note-attachments`) |
   | `MAX_UPLOAD_MB` | Maximum upload size in MB (default `4`) |

   > ⚠️ `.env` is git-ignored on purpose. Never commit real credentials.
   > `SUPABASE_SERVICE_KEY` bypasses Row Level Security — it must never reach the browser.

4. **Run the application**
   ```bash
   python src/main.py
   ```

5. **Access the application**
   - Open your browser at `http://localhost:5001`

## 📡 API Endpoints

### Notes
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/notes` | Get all notes (most recently updated first) |
| `POST` | `/api/notes` | Create a new note |
| `GET` | `/api/notes/<id>` | Get a specific note |
| `PUT` | `/api/notes/<id>` | Update a note |
| `DELETE` | `/api/notes/<id>` | Delete a note **and its attached files** |
| `GET` | `/api/notes/search?q=<query>` | Search notes by title or content |

### Translation
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/translate` | Translate a note into a target language |

Request body:
```json
{ "title": "My Note", "content": "今天天气很好", "target_language": "English" }
```

Response:
```json
{
  "detected_source_language": "Chinese",
  "target_language": "English",
  "translated_title": "My Note",
  "translated_content": "The weather is very nice today."
}
```

Supported target languages: Chinese, English, Japanese, Korean, French, German,
Spanish, Russian.

The prompt lives in `prompts/translate_prompt.md` and is kept separate from the
code, so it can be edited without touching Python.

### Attachments
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/notes/<note_id>/attachments` | Upload a file (`multipart/form-data`, field name `file`) |
| `GET` | `/api/notes/<note_id>/attachments` | List a note's attachments |
| `DELETE` | `/api/attachments/<attachment_id>` | Remove a file from storage and from the database |

Accepted types: images, PDF, plain text, Markdown, CSV, Office documents and zip
archives. Anything else is rejected with a descriptive error.

### Note response format
```json
{
  "id": 1,
  "title": "My Note Title",
  "content": "Note content here...",
  "created_at": "2026-10-02T11:26:38.123456",
  "updated_at": "2026-10-02T11:27:30.654321",
  "attachments": [
    {
      "id": 1,
      "note_id": 1,
      "filename": "diagram.png",
      "url": "https://<project>.supabase.co/storage/v1/object/public/note-attachments/notes/1/ab12....png",
      "mimetype": "image/png",
      "size": 20480,
      "is_image": true,
      "created_at": "2026-10-02T11:30:00.000000"
    }
  ]
}
```

## 🎨 User Interface

### Sidebar
- **Search Box**: Real-time search through note titles and content
- **New Note Button**: Create notes instantly
- **Notes List**: Scrollable list with title, preview and last-modified date

### Editor Panel
- **Title / Content**: Editable note body
- **Language selector + 🌐 Translate**: Translate the note; the result appears in a
  panel below the content, with a **Replace content** button (the original is kept
  until you choose to overwrite it)
- **💾 Save**: Manual save (debounced auto-save also runs while typing)
- **🗑️ Delete**: Appears only once the note has been saved
- **📎 Attachments**: Add files, see image thumbnails, and remove individual files.
  Also appears only after the note has been saved.

### Responsive behaviour
Font sizes, padding and button dimensions scale with `clamp()`, so the layout fills
the viewport rather than sitting in a fixed-width column. Breakpoints at 1100px,
768px and 480px adjust the grid and stack the editor toolbar.

## 🔒 Database Schema

Three tables, created automatically on first run via SQLAlchemy's `db.create_all()`.

```sql
CREATE TABLE note (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL
);

CREATE TABLE attachment (
    id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES note(id),
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(512) NOT NULL,   -- key inside the bucket (server-side only)
    url VARCHAR(1024) NOT NULL,           -- public URL handed to the browser
    mimetype VARCHAR(128),
    size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Note files live in Supabase Storage, not in the database — the `attachment` table
only records where to find them.

## ☁️ Deployment

### Stateless by design

The application stores nothing on the local filesystem: all data is in an external
PostgreSQL database and all files are in object storage. This is required for
serverless platforms such as Vercel, whose filesystem is wiped between requests.

### Environment variables

On the deployment platform, set the same variables as in `.env` (the file itself is
not deployed):

```
API_KEY, BASE_URL, MODEL_NAME, LLM_TIMEOUT,
DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY,
SUPABASE_BUCKET, MAX_UPLOAD_MB
```

### Database connection

Use the Supabase **Transaction pooler** connection string (host
`aws-0-<region>.pooler.supabase.com`, port `6543`, username `postgres.<project-ref>`).
The direct connection host (`db.<project-ref>.supabase.co`, port `5432`) resolves to
**IPv6 only**, which serverless platforms cannot reach.

When the `VERCEL` environment variable is present, the app automatically switches
SQLAlchemy to `NullPool`, since each serverless invocation is short-lived and holding
pooled connections open would exhaust the pooler.

### Upload size

`MAX_UPLOAD_MB` defaults to `4`, deliberately below Vercel's ~4.5 MB
serverless request-body limit, so uploads that work locally also work once deployed.

## 📱 Browser Compatibility

- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🆘 Troubleshooting

- **`DATABASE_URL is not set`** — copy `.env.example` to `.env` and fill it in.
- **`Supabase Storage is not configured`** — `SUPABASE_URL` and
  `SUPABASE_SERVICE_KEY` must both be set in `.env`.
- **`WinError 10048` / port 5001 already in use** — Flask's debug mode spawns a
  parent and child process; the child can outlive a hard shutdown. Find and kill it:
  `netstat -ano | findstr :5001`, then `taskkill /F /PID <pid>`.
- **Translation fails with "resource package does not support this model"** — the
  Gitee AI account's resource package does not cover that model. Change `MODEL_NAME`
  in `.env` to one your account supports.

## 🎯 Future Enhancements

- User authentication and multi-user support
- Note categories and tags
- Rich text formatting (bold, italic, lists)
- Extract text from attachments into the note body
- Export functionality (PDF, Markdown)
- Dark/light theme toggle

---

**Built with Flask, PostgreSQL (Supabase), and modern web technologies**
