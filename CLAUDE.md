# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run locally (without Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Start the app (SQLite used by default; DB auto-created at data/wildcard.db)
python app.py
# App runs on http://localhost:9000
```

### Run with Docker Compose (production-like)
```bash
# First time: copy and edit .env
cp .env.example .env   # Set COMFYUI_WILDCARD_PATH, SECRET_KEY, etc.

# Start all services (PostgreSQL + web)
docker-compose up -d

# View logs
docker-compose logs -f web

# Restart after code change (volumes are mounted, so just restart web)
docker-compose restart web
```

### Database migrations
Schema changes that `db.create_all()` can't apply to existing tables go into `_migrate_schema()` in `webapp/__init__.py`. Add raw SQL `ALTER TABLE` statements there — they run on every startup and are safe to re-run (errors are caught).

For large data migrations, use the standalone scripts:
```bash
python migrate_content_to_text.py
python migrate_flatten_categories.py
```

### One-off utility scripts (run inside the project root)
```bash
python bulk_import.py         # Bulk import wildcards from files
python init_categories.py     # Seed initial category tree
python auto_categorizer.py    # Auto-classify wildcards (169+ rules)
```

## Architecture

### Application factory
`app.py` is a thin entry point. The real setup is in `webapp/__init__.py` → `create_app()`:
1. Configures Flask + SQLAlchemy (SQLite default, PostgreSQL via `DATABASE_URL` env var)
2. Runs `_migrate_schema()` to add new columns to existing tables
3. Calls `webapp/init_data.py::init_all()` to seed required data
4. Registers all Blueprints

### Blueprint layout
| Blueprint | URL prefix | Purpose |
|-----------|-----------|---------|
| `pages_bp` | `/` | HTML page rendering |
| `categories_bp` | `/api/categories` | Category CRUD |
| `wildcards_bp` | `/api/wildcards` | Wildcard CRUD, batch ops, translation |
| `import_export_bp` | `/api` | TXT/ZIP import; TXT/JSON/CSV export |
| `settings_bp` | `/api` | App settings, translation settings |
| `profiles_bp` | `/api/translation-profiles` | Named translation profiles |
| `danbooru_bp` | `/api/danbooru` | Danbooru tag lookup/sync |
| `assistant_bp` | `/api/assistant` | AI chat assistant (action tags) |
| `comfy_bp` | registered in comfy_sync | ComfyUI file sync (wildcard txt sync) |
| `comfy_api_bp` | `/api/comfy` | ComfyUI API workflow execution |

Frontend is server-rendered Jinja2 templates (`webapp/templates/`) using Bootstrap 5.3 and vanilla JS. There is no build step — static files live in `webapp/static/`.

### Data models (`webapp/models.py`)
- **`Category`** — self-referencing tree (`parent_id → id`). `name` is the machine-safe slug (alphanumeric + `_`); `display_name` is human-readable. `level` is computed (0 = root). Unique constraint: `(parent_id, name)`.
- **`Wildcard`** — belongs to one `Category`. `content` is the English tag; `content_zh` is the translated Chinese. `translation_status` ∈ `{pending, translated, failed}`. `danbooru_status` ∈ `{valid, deprecated, not_found}`. Unique constraint: `(category_id, content)`.
- **`TranslationSetting`** — one row per provider (`ollama`, `gemini`, `openai`). Only one row has `is_active=True` at a time.
- **`TranslationProfile`** — named, reusable translation configurations (used by the assistant).
- **`ComfyWorkflow`** — stores ComfyUI API-format workflow JSON with name/description.
- **`ComfyJob`** — one row per execution: `prompt_id` (ComfyUI UUID), `status` ∈ `{queued, running, completed, failed}`, `output_images` (JSON array of `{filename, subfolder, type, node_id}`).
- **`AppSetting`** — generic key-value store (e.g. `comfyui_wildcard_path`, `comfyui_api_url`, `danbooru_login`).
- **`DanbooruTag`** — local cache of Danbooru tag metadata.
- **`PromptTemplate`** — saved prompt builder templates.

### Service layer (`webapp/services/`)
Business logic is extracted into services; routes delegate to them:
- `category_service.py` — CRUD, path resolution, ComfyUI filename encoding (`__` separator between hierarchy levels)
- `wildcard_service.py` — wildcard CRUD helpers
- `translation_service.py` — dispatches `translate()` / `batch_translate()` to the active provider helper
- `danbooru_service.py` — Danbooru API calls + local DB cache, thread-safe download lock
- `assistant_service.py` — AI assistant with structured `<action>` tags parsed server-side
- `comfy_api_service.py` — ComfyUI REST API client (`check_connection`, `queue_prompt`, `get_history`, `get_image_bytes`). Base URL defaults to `http://192.168.1.180:8188`, overridable via `AppSetting.comfyui_api_url`.
- `optimization_service.py` — batch/performance utilities

### AI / translation helpers (`webapp/helpers/`)
- `openai_helper.py` — Generic OpenAI-compatible client (`/v1/chat/completions`). Works with OpenAI, LM Studio, Ollama `/v1`, and any compatible endpoint. Supports `batch_translate()` via `ThreadPoolExecutor`.
- `ollama_helper.py` — Ollama-native API client.
- `gemini_helper.py` — Google Gemini API client.

`translation_service.py` selects the right helper based on `TranslationSetting.provider`.

### ComfyUI file sync
ComfyUI's AdaptivePrompts node requires a **flat directory** of `.txt` files. Category hierarchy is encoded in the filename using `__` as a separator:
- DB tree: `People → Artists → Anime Artists`
- File: `people__artists__anime_artists.txt`

The sync logic lives in `webapp/routes/api/comfy_sync.py` and `category_service.get_comfy_filepath_for_category()`.

### Configuration (env vars)
| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///data/wildcard.db` | DB connection string |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask session secret |
| `OLLAMA_BASE_URL` | auto-detected (docker vs local) | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen3:8b` | Default Ollama model |
| `COMFYUI_WILDCARD_PATH` | `./comfy_wildcard` | Mounted ComfyUI wildcard directory |

### ComfyUI workflow execution flow
1. User uploads API-format workflow JSON → stored as `ComfyWorkflow`
2. User embeds `%placeholder%` tokens in the JSON (e.g. `%model%`, `%prompt%`, `%seed%`, `%steps%`, `%width%`, `%height%`, `%cfg%`, `%sampler_name%`, `%scheduler%`)
3. `POST /api/comfy/workflows/<id>/run` substitutes tokens and calls `POST /prompt` on ComfyUI
   - `_INT_PLACEHOLDERS = {seed, steps, width, height}` → replaced as bare JSON integers
   - `_FLOAT_PLACEHOLDERS = {cfg, denoise}` → replaced as bare JSON floats
   - `seed = -1` is resolved to a random uint32 before substitution
4. Frontend polls `GET /api/comfy/jobs/<id>/status` every 3 s; backend checks `/history/<prompt_id>`
5. On completion, images are proxied through `GET /api/comfy/jobs/<id>/image?filename=...`

### ComfyUI wildcard sync (two approaches)
- **Local**: flat `.txt` files in `COMFYUI_WILDCARD_PATH`; category hierarchy encoded with `__` separator
- **SSH (planned)**: export to YAML at `192.168.1.180:D:\ComfyUI-aki-v1.6\ComfyUI\custom_nodes\ComfyUI-Impact-Pack\custom_wildcards\wildcards_all.yaml`

When running in Docker, `host.docker.internal` is mapped via `extra_hosts` to reach the host's Ollama.
