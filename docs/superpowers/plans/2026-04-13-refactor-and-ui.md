# App.py 重構 + UI 改版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 2036 行的 `app.py` 重構為 Flask Blueprint + Services 架構，整合 Wildcard/Category 管理頁面，新增 OpenAI-compatible 翻譯 provider，移除 Pollinations，簡化首頁。

**Architecture:** Flask Application Factory 模式 (`create_app()` 在 `webapp/__init__.py`)；業務邏輯抽至 `webapp/services/`；路由透過 Blueprint 組織；前端整合 Wildcard + Category 為雙欄單頁（Bootstrap col-3 / col-9）。

**Tech Stack:** Python 3.11, Flask 3.x, SQLAlchemy 2.x, Bootstrap 5, Vanilla JS, `requests` library

---

## 檔案對應總覽

| 動作 | 路徑 |
|------|------|
| 新建 | `webapp/__init__.py` |
| 新建 | `webapp/init_data.py` |
| 新建 | `webapp/routes/__init__.py` |
| 新建 | `webapp/routes/pages.py` |
| 新建 | `webapp/routes/api/__init__.py` |
| 新建 | `webapp/routes/api/categories.py` |
| 新建 | `webapp/routes/api/wildcards.py` |
| 新建 | `webapp/routes/api/import_export.py` |
| 新建 | `webapp/routes/api/comfy_sync.py` |
| 新建 | `webapp/routes/api/settings.py` |
| 新建 | `webapp/services/__init__.py` |
| 新建 | `webapp/services/category_service.py` |
| 新建 | `webapp/services/wildcard_service.py` |
| 新建 | `webapp/services/translation_service.py` |
| 新建 | `webapp/helpers/__init__.py` |
| 移入 | `webapp/helpers/ollama_helper.py` ← `ollama_helper.py` |
| 移入 | `webapp/helpers/gemini_helper.py` ← `gemini_helper.py` |
| 新建 | `webapp/helpers/openai_helper.py` |
| 新建 | `migrate_flatten_categories.py` |
| 修改 | `app.py` (縮減至 ~8 行) |
| 修改 | `webapp/models.py` (TranslationSetting 加 base_url) |
| 修改 | `webapp/templates/base.html` |
| 修改 | `webapp/templates/index.html` |
| 修改 | `webapp/templates/wildcards.html` (全新設計) |
| 修改 | `webapp/templates/translation_settings.html` |
| 刪除 | `ollama_helper.py` |
| 刪除 | `gemini_helper.py` |
| 刪除 | `pollinations_helper.py` |
| 刪除 | `webapp/templates/categories.html` |

---

## Phase 1：建立套件骨架

### Task 1：建立目錄結構與空白檔案

**Files:**
- Create: `webapp/__init__.py`
- Create: `webapp/init_data.py`
- Create: `webapp/routes/__init__.py`, `webapp/routes/api/__init__.py`
- Create: `webapp/routes/pages.py`, `webapp/routes/api/categories.py`
- Create: `webapp/routes/api/wildcards.py`, `webapp/routes/api/import_export.py`
- Create: `webapp/routes/api/comfy_sync.py`, `webapp/routes/api/settings.py`
- Create: `webapp/services/__init__.py`, `webapp/services/category_service.py`
- Create: `webapp/services/wildcard_service.py`, `webapp/services/translation_service.py`
- Create: `webapp/helpers/__init__.py`, `webapp/helpers/openai_helper.py`

- [ ] **Step 1: 建立目錄**

```bash
mkdir -p webapp/routes/api webapp/services webapp/helpers
```

- [ ] **Step 2: 建立所有 `__init__.py` 空白檔案**

```bash
touch webapp/routes/__init__.py webapp/routes/api/__init__.py
touch webapp/services/__init__.py webapp/helpers/__init__.py
```

- [ ] **Step 3: 建立 `webapp/__init__.py`（完整 create_app 工廠）**

```python
# -*- coding: utf-8 -*-
"""Flask Application Factory."""

from flask import Flask
from webapp.models import db
from sqlalchemy import text
import os


def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # --- Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 'sqlite:///data/wildcard.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['OLLAMA_MODEL'] = os.getenv('OLLAMA_MODEL', 'qwen3:8b')

    _in_docker = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
    _default_ollama = 'http://host.docker.internal:11434' if _in_docker else 'http://localhost:11434'
    app.config['OLLAMA_BASE_URL'] = os.getenv('OLLAMA_BASE_URL', _default_ollama)

    # --- Database ---
    db.init_app(app)

    with app.app_context():
        db.create_all()
        _migrate_schema()
        from webapp.init_data import init_all
        init_all()

    # --- Blueprints ---
    _register_blueprints(app)
    return app


def _migrate_schema():
    """Add columns that db.create_all() won't add to existing tables."""
    statements = [
        "ALTER TABLE translation_settings ADD COLUMN IF NOT EXISTS base_url VARCHAR(500)",
    ]
    for sql in statements:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()
            # SQLite fallback (no IF NOT EXISTS)
            try:
                db.session.execute(text(sql.replace(' IF NOT EXISTS', '')))
                db.session.commit()
            except Exception:
                db.session.rollback()


def _register_blueprints(app):
    from webapp.routes.pages import pages_bp
    from webapp.routes.api.categories import categories_bp
    from webapp.routes.api.wildcards import wildcards_bp
    from webapp.routes.api.import_export import import_export_bp
    from webapp.routes.api.comfy_sync import comfy_bp
    from webapp.routes.api.settings import settings_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(wildcards_bp, url_prefix='/api/wildcards')
    app.register_blueprint(import_export_bp, url_prefix='/api')
    app.register_blueprint(comfy_bp, url_prefix='/api/comfy-wildcard')
    app.register_blueprint(settings_bp, url_prefix='/api')
```

- [ ] **Step 4: 建立 `webapp/init_data.py`**

```python
# -*- coding: utf-8 -*-
"""Application data initialization (seeding defaults)."""

from webapp.models import db, Category, AppSetting, TranslationSetting
from sqlalchemy.exc import OperationalError
import os

_DEFAULT_PROMPT_ZH = """你是一個專業的AI繪圖提示詞翻譯助手。你的任務是將英文的AI繪圖提示詞（wildcard）翻譯成簡潔、準確的繁體中文。

翻譯規則：
1. 只返回翻譯結果，不要加任何解釋或額外文字
2. 保持原文的核心含義
3. 對於藝術家名字，保留原文並在括號內註明中文（如果知名）
4. 對於專業術語，使用常見的中文翻譯
5. 保持簡潔，通常不超過原文長度的2倍"""


def init_all():
    init_app_settings()
    init_categories()
    init_translation_settings()


def init_app_settings():
    setting = AppSetting.query.filter_by(key='comfyui_wildcard_path').first()
    if not setting:
        default_path = os.getenv('COMFYUI_WILDCARD_PATH', '/app/comfy_wildcard')
        db.session.add(AppSetting(key='comfyui_wildcard_path', value=default_path))
        db.session.commit()
        print(f"✓ ComfyUI 路徑初始化: {default_path}")


def init_categories():
    if Category.query.count() > 0:
        return
    try:
        from init_categories import CATEGORY_TREE, create_category_tree
        for root_data in CATEGORY_TREE:
            create_category_tree(root_data)
        db.session.commit()
        print(f"✓ 已初始化 {Category.query.count()} 個分類")
    except Exception as e:
        print(f"初始化分類失敗: {e}")
        db.session.rollback()


def init_translation_settings():
    try:
        # 移除舊的 Pollinations 設定（如存在）
        pollinations = TranslationSetting.query.filter_by(provider='pollinations').first()
        if pollinations:
            db.session.delete(pollinations)
            db.session.commit()
            print("✓ 已移除 Pollinations 設定")

        if TranslationSetting.query.count() > 0:
            # 確保 openai provider 存在
            if not TranslationSetting.query.filter_by(provider='openai').first():
                db.session.add(TranslationSetting(
                    provider='openai', is_active=False,
                    base_url='https://api.openai.com/v1',
                    model_name='gpt-4o-mini', temperature=0.3,
                    system_prompt=_DEFAULT_PROMPT_ZH
                ))
                db.session.commit()
                print("✓ 已新增 OpenAI-compatible 設定")
            return

        # 全新初始化
        db.session.add(TranslationSetting(
            provider='ollama', is_active=True,
            model_name='qwen3:8b', temperature=0.3,
            system_prompt=_DEFAULT_PROMPT_ZH
        ))
        db.session.add(TranslationSetting(
            provider='gemini', is_active=False,
            model_name='models/gemini-flash-latest', temperature=0.3,
            system_prompt=_DEFAULT_PROMPT_ZH
        ))
        db.session.add(TranslationSetting(
            provider='openai', is_active=False,
            base_url='https://api.openai.com/v1',
            model_name='gpt-4o-mini', temperature=0.3,
            system_prompt=_DEFAULT_PROMPT_ZH
        ))
        db.session.commit()
        print("✓ 翻譯設定初始化完成")

    except OperationalError as e:
        print(f"資料庫 schema 錯誤: {e}")
        db.session.rollback()
    except Exception as e:
        print(f"初始化翻譯設定錯誤: {e}")
        db.session.rollback()
```

- [ ] **Step 5: 更新 `app.py`（縮減為 8 行）**

```python
# -*- coding: utf-8 -*-
"""Wildcard 管理系統 - 入口點"""

from webapp import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
```

- [ ] **Step 6: 建立空白 Blueprint stub（讓應用可以啟動）**

`webapp/routes/pages.py`:
```python
from flask import Blueprint, render_template
pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    return render_template('index.html')

@pages_bp.route('/wildcards')
def wildcards_page():
    return render_template('wildcards.html')

@pages_bp.route('/import')
def import_page():
    return render_template('import.html')

@pages_bp.route('/export')
def export_page():
    return render_template('export.html')

@pages_bp.route('/comfy-monitor')
def comfy_monitor_page():
    return render_template('comfy_monitor.html')

@pages_bp.route('/translation-settings')
def translation_settings_page():
    return render_template('translation_settings.html')

@pages_bp.route('/prompt-builder')
def prompt_builder_page():
    return render_template('prompt_builder.html')
```

各 API blueprint stub（`webapp/routes/api/categories.py` 等）：
```python
from flask import Blueprint
categories_bp = Blueprint('categories', __name__)
# Routes added in Task 5
```
（wildcards_bp、import_export_bp、comfy_bp、settings_bp 同樣的 stub 格式）

- [ ] **Step 7: 驗證應用可以啟動**

```bash
python app.py
# Expected: * Running on http://0.0.0.0:9000
# No ImportError, no AttributeError
```

訪問 `http://localhost:9000`，確認頁面載入（此時 API 尚未遷移，頁面可能 JS 錯誤，但不 crash）。

- [ ] **Step 8: Commit**

```bash
git add webapp/__init__.py webapp/init_data.py webapp/routes/ webapp/services/ webapp/helpers/ app.py
git commit -m "refactor: create Flask Blueprint skeleton + create_app() factory"
```

---

### Task 2：移動 Helpers + 建立 OpenAI Helper

**Files:**
- Create: `webapp/helpers/ollama_helper.py` (copy from root)
- Create: `webapp/helpers/gemini_helper.py` (copy from root)
- Create: `webapp/helpers/openai_helper.py` (new)
- Delete: `ollama_helper.py`, `gemini_helper.py`, `pollinations_helper.py`

- [ ] **Step 1: 複製 ollama_helper 和 gemini_helper**

```bash
cp ollama_helper.py webapp/helpers/ollama_helper.py
cp gemini_helper.py webapp/helpers/gemini_helper.py
```

- [ ] **Step 2: 更新 `webapp/helpers/ollama_helper.py` 開頭 import（確認無根目錄相依）**

開啟 `webapp/helpers/ollama_helper.py`，確認所有 import 都是標準庫（`requests`, `json`, `time`, `typing`, `concurrent.futures`）。不需修改 class 邏輯。

- [ ] **Step 3: 建立 `webapp/helpers/openai_helper.py`**

```python
# -*- coding: utf-8 -*-
"""Generic OpenAI-compatible API helper.

Works with: OpenAI, LM Studio, Ollama (/v1), any OpenAI-compatible endpoint.
api_key may be empty for local unauthenticated services.
"""

import requests
from typing import Optional
import concurrent.futures


class OpenAIHelper:
    def __init__(self, base_url: str, api_key: str = '', model: str = 'gpt-4o-mini'):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self._headers = {'Content-Type': 'application/json'}
        if api_key:
            self._headers['Authorization'] = f'Bearer {api_key}'

    def translate_to_chinese(
        self, text: str,
        system_prompt: str = '',
        temperature: float = 0.3
    ) -> Optional[str]:
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text},
            ],
            'temperature': temperature,
        }
        try:
            resp = requests.post(
                f'{self.base_url}/chat/completions',
                json=payload, headers=self._headers, timeout=30
            )
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f'[OpenAIHelper] translate error: {e}')
            return None

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(
                f'{self.base_url}/models',
                headers=self._headers, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return sorted([m['id'] for m in data.get('data', [])])
        except Exception as e:
            print(f'[OpenAIHelper] list_models error: {e}')
            return []

    def check_connection(self) -> bool:
        try:
            resp = requests.get(
                f'{self.base_url}/models',
                headers=self._headers, timeout=5
            )
            return resp.status_code < 500
        except Exception:
            return False

    def batch_translate(
        self, texts: list[str],
        system_prompt: str = '',
        temperature: float = 0.3,
        max_workers: int = 4
    ) -> list[Optional[str]]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.translate_to_chinese, t, system_prompt, temperature)
                for t in texts
            ]
            return [f.result() for f in futures]
```

- [ ] **Step 4: 刪除根目錄的舊 helper 檔案**

```bash
rm ollama_helper.py gemini_helper.py pollinations_helper.py
```

- [ ] **Step 5: 驗證 import 可以解析**

```bash
python -c "from webapp.helpers.ollama_helper import OllamaHelper; print('OK')"
python -c "from webapp.helpers.gemini_helper import GeminiHelper; print('OK')"
python -c "from webapp.helpers.openai_helper import OpenAIHelper; print('OK')"
```

Expected: 三行都印出 `OK`，無 ImportError。

- [ ] **Step 6: Commit**

```bash
git add webapp/helpers/ && git rm ollama_helper.py gemini_helper.py pollinations_helper.py
git commit -m "refactor: move helpers into webapp/helpers/, add OpenAIHelper"
```

---

## Phase 2：Services 層

### Task 3：建立 `category_service.py`

**Files:**
- Modify: `webapp/services/category_service.py`

- [ ] **Step 1: 寫入完整 `webapp/services/category_service.py`**

```python
# -*- coding: utf-8 -*-
"""Category business logic — CRUD, ComfyUI filepath helpers."""

from pathlib import Path
from webapp.models import db, Category, AppSetting
import os


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_comfy_wildcard_path() -> str:
    setting = AppSetting.query.filter_by(key='comfyui_wildcard_path').first()
    return setting.value if setting else os.getenv('COMFYUI_WILDCARD_PATH', '/app/comfy_wildcard')


def get_comfy_filepath_for_category(category: Category, comfy_path_str: str):
    """Return (dir_path: Path, filename: str) for a category's .txt file.

    Works correctly both before and after category flattening:
    - Before: traverses parent chain → people__artists__anime_artists.txt
    - After:  name IS already the full key → people__artists__anime_artists.txt
    """
    parts = []
    current = category
    while current:
        parts.insert(0, current.name)
        current = current.parent
    filename = '__'.join(parts) + '.txt'
    return Path(comfy_path_str), filename


def get_category_from_filename(filename: str) -> Category | None:
    """Find a category from a flat filename (e.g. people__artists__anime.txt)."""
    name_without_ext = filename.removesuffix('.txt')
    parts = name_without_ext.split('__')

    current = None
    for part in parts:
        if current is None:
            current = Category.query.filter_by(name=part, parent_id=None).first()
        else:
            current = Category.query.filter_by(name=part, parent_id=current.id).first()
        if not current:
            return None
    return current


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_category(data: dict) -> Category:
    parent_id = data.get('parent_id')
    level = 0
    if parent_id:
        parent = Category.query.get_or_404(parent_id)
        level = parent.level + 1

    category = Category(
        name=data['name'],
        display_name=data['display_name'],
        description=data.get('description'),
        color=data.get('color', '#6c757d'),
        sort_order=data.get('sort_order', 0),
        parent_id=parent_id,
        level=level,
    )
    db.session.add(category)
    db.session.commit()
    return category


def update_category(category: Category, data: dict) -> Category:
    category.display_name = data.get('display_name', category.display_name)
    category.description = data.get('description', category.description)
    category.color = data.get('color', category.color)
    category.sort_order = data.get('sort_order', category.sort_order)

    if 'parent_id' in data and category.parent_id != data['parent_id']:
        new_parent_id = data.get('parent_id')
        # Circular dependency check
        temp = Category.query.get(new_parent_id) if new_parent_id else None
        while temp:
            if temp.id == category.id:
                raise ValueError('不能將類別設定為自己的子類別')
            temp = temp.parent

        category.parent_id = new_parent_id
        parent_level = Category.query.get(new_parent_id).level if new_parent_id else -1
        _update_levels_recursively(category, parent_level + 1)

    db.session.commit()
    return category


def delete_category(category: Category) -> dict:
    wildcard_count, child_count = _count_descendants(category)
    comfy_path_str = get_comfy_wildcard_path()
    if comfy_path_str:
        _remove_category_from_comfy(category, comfy_path_str)
    db.session.delete(category)
    db.session.commit()
    return {'deleted_wildcards': wildcard_count, 'deleted_children': child_count}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _update_levels_recursively(cat: Category, new_level: int):
    cat.level = new_level
    for child in cat.children:
        _update_levels_recursively(child, new_level + 1)


def _count_descendants(cat: Category) -> tuple[int, int]:
    wc = len(cat.wildcards)
    cc = len(cat.children)
    for child in cat.children:
        w, c = _count_descendants(child)
        wc += w
        cc += c
    return wc, cc


def _remove_category_from_comfy(cat: Category, comfy_path_str: str):
    for wildcard in cat.wildcards:
        if not wildcard.is_active:
            continue
        try:
            dir_path, filename = get_comfy_filepath_for_category(cat, comfy_path_str)
            filepath = dir_path / filename
            if filepath.exists():
                lines = filepath.read_text(encoding='utf-8').splitlines(keepends=True)
                filepath.write_text(
                    ''.join(l for l in lines if l.strip() != wildcard.content),
                    encoding='utf-8',
                )
        except Exception as e:
            print(f'[category_service] 移除 ComfyUI 檔案失敗: {e}')
    for child in cat.children:
        _remove_category_from_comfy(child, comfy_path_str)
```

- [ ] **Step 2: 驗證 import**

```bash
python -c "from webapp.services.category_service import create_category; print('OK')"
```

Expected: `OK`

---

### Task 4：建立 `wildcard_service.py` 和 `translation_service.py`

**Files:**
- Modify: `webapp/services/wildcard_service.py`
- Modify: `webapp/services/translation_service.py`

- [ ] **Step 1: 寫入 `webapp/services/wildcard_service.py`**

```python
# -*- coding: utf-8 -*-
"""Wildcard business logic — CRUD, ComfyUI file sync, batch ops."""

from pathlib import Path
from webapp.models import db, Wildcard, Category
from webapp.services.category_service import get_comfy_wildcard_path, get_comfy_filepath_for_category


def sync_active_to_comfy(wildcard: Wildcard):
    """Append wildcard content to its .txt file (activate)."""
    comfy_path = get_comfy_wildcard_path()
    if not comfy_path or not wildcard.category:
        return
    dir_path, filename = get_comfy_filepath_for_category(wildcard.category, comfy_path)
    filepath = dir_path / filename
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f'\n{wildcard.content}')
    except Exception as e:
        print(f'[wildcard_service] sync activate error: {e}')


def remove_from_comfy(wildcard: Wildcard):
    """Remove wildcard content from its .txt file (deactivate)."""
    comfy_path = get_comfy_wildcard_path()
    if not comfy_path or not wildcard.category:
        return
    dir_path, filename = get_comfy_filepath_for_category(wildcard.category, comfy_path)
    filepath = dir_path / filename
    try:
        if not filepath.exists():
            return
        lines = filepath.read_text(encoding='utf-8').splitlines(keepends=True)
        filepath.write_text(
            ''.join(l for l in lines if l.strip() != wildcard.content),
            encoding='utf-8',
        )
    except Exception as e:
        print(f'[wildcard_service] sync deactivate error: {e}')


def batch_update_active(ids: list[int], is_active: bool) -> dict:
    """Batch enable/disable wildcards and sync to ComfyUI."""
    wildcards = Wildcard.query.filter(Wildcard.id.in_(ids)).all()
    updated = 0
    errors = 0
    for wc in wildcards:
        if wc.is_active == is_active:
            continue
        try:
            if is_active:
                sync_active_to_comfy(wc)
            else:
                remove_from_comfy(wc)
            wc.is_active = is_active
            updated += 1
        except Exception as e:
            print(f'[wildcard_service] batch_update error for id={wc.id}: {e}')
            errors += 1
    db.session.commit()
    return {'updated': updated, 'errors': errors}
```

- [ ] **Step 2: 寫入 `webapp/services/translation_service.py`**

```python
# -*- coding: utf-8 -*-
"""Translation dispatch — routes requests to the active provider helper."""

from webapp.models import TranslationSetting
from flask import current_app
from typing import Optional


def get_active_setting() -> TranslationSetting | None:
    return TranslationSetting.query.filter_by(is_active=True).first()


def translate(text: str) -> Optional[str]:
    """Translate using the currently active provider."""
    setting = get_active_setting()
    if not setting:
        raise ValueError('沒有啟用的翻譯服務')
    return _dispatch(text, setting.provider, setting)


def batch_translate(texts: list[str]) -> list[Optional[str]]:
    setting = get_active_setting()
    if not setting:
        raise ValueError('沒有啟用的翻譯服務')
    helper = _build_helper(setting.provider, setting)
    return helper.batch_translate(
        texts,
        system_prompt=setting.system_prompt,
        temperature=setting.temperature,
    )


def translate_with_override(text: str, provider: str, settings_dict: dict,
                             db_setting: TranslationSetting = None) -> Optional[str]:
    """Translate using explicit settings (for test endpoint)."""
    # Build a temporary mock object from dict
    class _TmpSetting:
        pass
    tmp = _TmpSetting()
    tmp.provider = provider
    tmp.model_name = settings_dict.get('model_name', '')
    tmp.temperature = float(settings_dict.get('temperature', 0.3))
    tmp.system_prompt = settings_dict.get('system_prompt', '')
    tmp.api_key = settings_dict.get('api_key') or (db_setting.api_key if db_setting else '')
    tmp.base_url = settings_dict.get('base_url') or (db_setting.base_url if db_setting else '')
    return _dispatch(text, provider, tmp)


def list_models(provider: str, base_url: str = None, api_key: str = None) -> list[str]:
    if provider == 'openai':
        from webapp.helpers.openai_helper import OpenAIHelper
        setting = TranslationSetting.query.filter_by(provider='openai').first()
        _url = base_url or (setting.base_url if setting else '')
        _key = api_key or (setting.api_key if setting else '')
        return OpenAIHelper(base_url=_url, api_key=_key).list_models()
    return []


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _dispatch(text: str, provider: str, setting) -> Optional[str]:
    helper = _build_helper(provider, setting)
    return helper.translate_to_chinese(
        text,
        system_prompt=setting.system_prompt,
        temperature=setting.temperature,
    )


def _build_helper(provider: str, setting):
    if provider == 'ollama':
        from webapp.helpers.ollama_helper import OllamaHelper
        return OllamaHelper(
            base_url=current_app.config['OLLAMA_BASE_URL'],
            model=setting.model_name,
        )
    elif provider == 'gemini':
        from webapp.helpers.gemini_helper import GeminiHelper
        return GeminiHelper(api_key=setting.api_key, model=setting.model_name)
    elif provider == 'openai':
        from webapp.helpers.openai_helper import OpenAIHelper
        return OpenAIHelper(
            base_url=setting.base_url or 'https://api.openai.com/v1',
            api_key=setting.api_key or '',
            model=setting.model_name,
        )
    raise ValueError(f'不支援的 provider: {provider}')
```

- [ ] **Step 3: 驗證 import**

```bash
python -c "from webapp.services.wildcard_service import batch_update_active; print('OK')"
python -c "from webapp.services.translation_service import translate; print('OK')"
```

Expected: 兩行都 `OK`。

---

## Phase 3：Blueprint 路由遷移

> **重要原則**：每個 Blueprint 的路由邏輯直接從 `app.py` 對應段落複製，替換：
> - `@app.route(...)` → `@<blueprint>.route(...)`
> - `app.config[...]` → `current_app.config[...]`
> - 直接呼叫 helper 的業務邏輯 → 改呼叫 service 函式

### Task 5：Categories Blueprint

**Files:**
- Modify: `webapp/routes/api/categories.py`

- [ ] **Step 1: 實作 `webapp/routes/api/categories.py`**

從 `app.py` 第 261–410 行複製 4 個路由，替換如下：

```python
# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from webapp.models import db, Category, Wildcard
from webapp.services import category_service
from sqlalchemy import func

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('', methods=['GET'])
def api_get_categories():
    tree_mode = request.args.get('tree', 'false').lower() == 'true'
    parent_id = request.args.get('parent_id', type=int)

    if parent_id is not None:
        cats = Category.query.filter_by(parent_id=parent_id).order_by(Category.sort_order).all()
        return jsonify([c.to_dict() for c in cats])
    if tree_mode:
        roots = Category.query.filter_by(parent_id=None).order_by(Category.sort_order).all()
        return jsonify([c.to_dict(include_children=True) for c in roots])
    cats = Category.query.order_by(Category.level, Category.sort_order).all()
    return jsonify([c.to_dict() for c in cats])


@categories_bp.route('', methods=['POST'])
def api_create_category():
    data = request.json
    try:
        category = category_service.create_category(data)
        return jsonify(category.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@categories_bp.route('/<int:category_id>', methods=['PUT'])
def api_update_category(category_id):
    category = Category.query.get_or_404(category_id)
    try:
        category = category_service.update_category(category, request.json)
        return jsonify(category.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@categories_bp.route('/<int:category_id>', methods=['DELETE'])
def api_delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    try:
        result = category_service.delete_category(category)
        return jsonify({'message': '類別已刪除', **result})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 2: 驗證 categories API**

啟動 `python app.py`，執行：

```bash
curl http://localhost:9000/api/categories
# Expected: JSON array (empty or with categories)

curl -X POST http://localhost:9000/api/categories \
  -H 'Content-Type: application/json' \
  -d '{"name":"test","display_name":"Test"}'
# Expected: 201 with new category JSON
```

- [ ] **Step 3: Commit**

```bash
git add webapp/routes/api/categories.py webapp/services/category_service.py
git commit -m "refactor: extract categories Blueprint + category_service"
```

---

### Task 6：Wildcards Blueprint

**Files:**
- Modify: `webapp/routes/api/wildcards.py`
- Modify: `webapp/services/wildcard_service.py`

- [ ] **Step 1: 實作 `webapp/routes/api/wildcards.py`**

從 `app.py` 第 412–730 行複製，涵蓋：GET list、POST create、PUT update、DELETE、batch-delete、batch-update-category、batch-update-active、batch-translate。

```python
# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
from webapp.models import db, Wildcard, Category, TranslationSetting
from webapp.services import wildcard_service, translation_service
from sqlalchemy import func

wildcards_bp = Blueprint('wildcards', __name__)


@wildcards_bp.route('', methods=['GET'])
def api_get_wildcards():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    is_active = request.args.get('is_active', type=str)
    untranslated_first = request.args.get('untranslated_first', 'false').lower() == 'true'

    query = Wildcard.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Wildcard.content.ilike(f'%{search}%'))
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')

    if untranslated_first:
        query = query.order_by(
            db.case((Wildcard.content_zh == None, 0), (Wildcard.content_zh == '', 0), else_=1),
            Wildcard.content
        )
    else:
        query = query.order_by(Wildcard.content)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'items': [w.to_dict() for w in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@wildcards_bp.route('', methods=['POST'])
def api_create_wildcard():
    data = request.json
    category = Category.query.get_or_404(data['category_id'])
    wildcard = Wildcard(
        content=data['content'],
        content_zh=data.get('content_zh'),
        category_id=data['category_id'],
        is_active=data.get('is_active', True),
        tags=','.join(data.get('tags', [])) if isinstance(data.get('tags'), list) else data.get('tags', ''),
        notes=data.get('notes'),
        priority=data.get('priority', 0),
    )
    try:
        db.session.add(wildcard)
        db.session.flush()
        if wildcard.is_active:
            wildcard_service.sync_active_to_comfy(wildcard)
        db.session.commit()
        return jsonify(wildcard.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@wildcards_bp.route('/<int:wildcard_id>', methods=['PUT'])
def api_update_wildcard(wildcard_id):
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    data = request.json
    old_active = wildcard.is_active
    new_active = data.get('is_active', old_active)

    wildcard.content = data.get('content', wildcard.content)
    wildcard.content_zh = data.get('content_zh', wildcard.content_zh)
    wildcard.category_id = data.get('category_id', wildcard.category_id)
    wildcard.priority = data.get('priority', wildcard.priority)
    wildcard.tags = data.get('tags', wildcard.tags)
    wildcard.notes = data.get('notes', wildcard.notes)

    if old_active != new_active:
        wildcard.is_active = new_active
        if new_active:
            wildcard_service.sync_active_to_comfy(wildcard)
        else:
            wildcard_service.remove_from_comfy(wildcard)
    else:
        wildcard.is_active = new_active

    db.session.commit()
    return jsonify(wildcard.to_dict())


@wildcards_bp.route('/<int:wildcard_id>', methods=['DELETE'])
def api_delete_wildcard(wildcard_id):
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    if wildcard.is_active:
        wildcard_service.remove_from_comfy(wildcard)
    db.session.delete(wildcard)
    db.session.commit()
    return '', 204


@wildcards_bp.route('/batch-delete', methods=['POST'])
def api_batch_delete():
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'error': '未提供 ID'}), 400
    Wildcard.query.filter(Wildcard.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'deleted': len(ids)})


@wildcards_bp.route('/batch-update-category', methods=['POST'])
def api_batch_update_category():
    data = request.json
    ids = data.get('ids', [])
    category_id = data.get('category_id')
    if not ids or not category_id:
        return jsonify({'error': '缺少 ids 和 category_id'}), 400
    category = Category.query.get_or_404(category_id)
    updated = Wildcard.query.filter(Wildcard.id.in_(ids)).update(
        {'category_id': category_id}, synchronize_session=False)
    db.session.commit()
    return jsonify({'message': f'已移動 {updated} 個到 "{category.display_name}"', 'updated': updated})


@wildcards_bp.route('/batch-update-active', methods=['POST'])
def api_batch_update_active():
    data = request.json
    ids = data.get('ids', [])
    is_active = data.get('is_active')
    if not ids or is_active is None:
        return jsonify({'error': '缺少 ids 和 is_active'}), 400
    result = wildcard_service.batch_update_active(ids, is_active)
    action = '啟用' if is_active else '停用'
    msg = f'成功{action} {result["updated"]} 個'
    if result['errors']:
        msg += f'，{result["errors"]} 個檔案同步失敗'
    return jsonify({'message': msg, **result})


@wildcards_bp.route('/batch-translate', methods=['POST'])
def api_batch_translate():
    data = request.json
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': '未提供 ID'}), 400

    wildcards = Wildcard.query.filter(Wildcard.id.in_(ids)).all()
    texts = [w.content for w in wildcards]

    try:
        results = translation_service.batch_translate(texts)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'翻譯失敗: {e}'}), 500

    translated_count = 0
    for wildcard, result in zip(wildcards, results):
        if result:
            wildcard.content_zh = result
            wildcard.translation_status = 'translated'
            translated_count += 1
        else:
            wildcard.translation_status = 'failed'
    db.session.commit()
    return jsonify({'translated': translated_count, 'total': len(wildcards)})
```

- [ ] **Step 2: 驗證 wildcards API**

```bash
curl http://localhost:9000/api/wildcards?per_page=5
# Expected: {"items":[...],"total":N,"pages":M,"current_page":1}
```

- [ ] **Step 3: Commit**

```bash
git add webapp/routes/api/wildcards.py webapp/services/wildcard_service.py
git commit -m "refactor: extract wildcards Blueprint + wildcard_service"
```

---

### Task 7：Import/Export + ComfyUI Sync Blueprints

**Files:**
- Modify: `webapp/routes/api/import_export.py`
- Modify: `webapp/routes/api/comfy_sync.py`

- [ ] **Step 1: 實作 `webapp/routes/api/import_export.py`**

從 `app.py` 第 860–1160 行複製所有 import/export/history 路由。替換：
- `@app.route('/api/import/...')` → `@import_export_bp.route('/import/...')`
- `@app.route('/api/export/...')` → `@import_export_bp.route('/export/...')`
- `app.config` → `current_app.config`
- 保留同檔案內的 helper 函式 `import_txt_file()`, `import_from_directory()`

Blueprint header：
```python
from flask import Blueprint, request, jsonify, send_file, current_app
from webapp.models import db, Wildcard, Category, ImportHistory
from webapp.services.category_service import get_comfy_wildcard_path
import os, zipfile, re, tempfile, uuid
from pathlib import Path
from werkzeug.utils import secure_filename

import_export_bp = Blueprint('import_export', __name__)
```

- [ ] **Step 2: 實作 `webapp/routes/api/comfy_sync.py`**

從 `app.py` 第 1162–1465 行複製所有 `/api/comfy-wildcard/` 路由。替換：
- `@app.route('/api/comfy-wildcard/...')` → `@comfy_bp.route('/...')`
- `get_comfy_filepath_for_category` → `from webapp.services.category_service import get_comfy_filepath_for_category, get_comfy_wildcard_path, get_category_from_filename`

Blueprint header：
```python
from flask import Blueprint, request, jsonify, current_app
from webapp.models import db, Category, Wildcard, ImportHistory
from webapp.services.category_service import (
    get_comfy_wildcard_path, get_comfy_filepath_for_category, get_category_from_filename
)
import os
from pathlib import Path

comfy_bp = Blueprint('comfy', __name__)
```

- [ ] **Step 3: 驗證 import/comfy endpoints**

```bash
curl http://localhost:9000/api/import/history
# Expected: JSON array

curl http://localhost:9000/api/comfy-wildcard/scan
# Expected: {"files": [...]} or similar
```

- [ ] **Step 4: Commit**

```bash
git add webapp/routes/api/import_export.py webapp/routes/api/comfy_sync.py
git commit -m "refactor: extract import_export + comfy_sync Blueprints"
```

---

### Task 8：Settings Blueprint + Prompt Builder + Slim app.py

**Files:**
- Modify: `webapp/routes/api/settings.py`
- Modify: `webapp/routes/pages.py`
- Verify: `app.py` 已是最終形態

- [ ] **Step 1: 實作 `webapp/routes/api/settings.py`**

從 `app.py` 第 1465–1805 行複製，涵蓋：
- `/api/stats` (GET)
- `/api/settings/comfy-path` (GET, PUT)
- `/api/data/clear` (POST)
- `/api/translation-settings` (GET)
- `/api/translation-settings/<provider>` (PUT)
- `/api/translation-settings/activate` (POST)
- `/api/translation-settings/test` (POST)
- `/api/translation-settings/pollinations/models` → **刪除此路由**
- **新增** `/api/translation-settings/openai/probe-models` (POST)（見 Task 9）

Blueprint header：
```python
from flask import Blueprint, request, jsonify, current_app
from webapp.models import db, Category, Wildcard, ImportHistory, AppSetting, TranslationSetting
from webapp.services import translation_service
from sqlalchemy import func

settings_bp = Blueprint('settings', __name__)
```

替換翻譯 dispatch 邏輯：原本 `get_translation_service()` → 改用 `translation_service._build_helper()`（或直接 dispatch）。

- [ ] **Step 2: 將 Prompt Builder API 路由加入 `webapp/routes/pages.py`**

從 `app.py` 第 1805–2036 行複製兩個路由（`/api/prompt-builder/wildcards` 和 `/api/prompt-builder/preview`）到 `pages.py`：

```python
# 加在 pages.py 底部
from webapp.models import db, Category, Wildcard

@pages_bp.route('/api/prompt-builder/wildcards', methods=['GET'])
def api_get_prompt_builder_wildcards():
    # 複製自 app.py 第 1806-1844 行，無需修改
    ...

@pages_bp.route('/api/prompt-builder/preview', methods=['POST'])
def api_preview_prompt():
    # 複製自 app.py 第 1847-2036 行，無需修改
    import random, re
    ...
```

- [ ] **Step 3: 確認 `app.py` 只有 8 行**

```python
# app.py 最終版本
from webapp import create_app
app = create_app()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
```

- [ ] **Step 4: 全面驗證**

```bash
python app.py
# 啟動無 error

curl http://localhost:9000/api/stats
# Expected: {"total_wildcards":N, "active_wildcards":M, "total_categories":K}

curl http://localhost:9000/api/translation-settings
# Expected: JSON array with ollama, gemini, openai providers
```

瀏覽器訪問所有頁面，確認無 500 error。

- [ ] **Step 5: Commit**

```bash
git add webapp/routes/ app.py
git commit -m "refactor: complete Blueprint migration, app.py reduced to 8 lines"
```

---

## Phase 4：翻譯 Provider 更新

### Task 9：OpenAI-compatible Provider 完整整合

**Files:**
- Modify: `webapp/models.py` (to_dict 加 base_url)
- Modify: `webapp/routes/api/settings.py` (新增 probe-models endpoint，移除 pollinations endpoint)

- [ ] **Step 1: 更新 `webapp/models.py` 的 `TranslationSetting.to_dict()`**

找到 `to_dict()` 方法（約第 213 行），在 `"has_api_key"` 前新增 `base_url`：

```python
def to_dict(self):
    return {
        "provider": self.provider,
        "is_active": self.is_active,
        "model_name": self.model_name,
        "temperature": self.temperature,
        "system_prompt": self.system_prompt,
        "base_url": self.base_url,          # ← 新增
        "has_api_key": bool(self.api_key)
    }
```

- [ ] **Step 2: 在 `settings.py` 的 PUT `/api/translation-settings/<provider>` 加入 base_url 處理**

找到 `api_update_translation_setting` 函式，在 system_prompt 更新後加：

```python
# 處理 openai 的 base_url
if provider == 'openai' and 'base_url' in data and data['base_url']:
    setting.base_url = data['base_url']
# 處理 api_key（openai 和 gemini）
if provider in ('gemini', 'openai') and 'api_key' in data and data['api_key']:
    setting.api_key = data['api_key']
```

- [ ] **Step 3: 在 `settings.py` 新增 probe-models endpoint**

```python
@settings_bp.route('/translation-settings/openai/probe-models', methods=['POST'])
def api_probe_openai_models():
    """Probe OpenAI-compatible endpoint for available models.
    Uses the base_url and api_key from request body (not DB),
    so user can test before saving.
    """
    data = request.json or {}
    base_url = data.get('base_url', '').strip()
    api_key = data.get('api_key', '').strip()

    if not base_url:
        return jsonify({'error': '請提供 Base URL'}), 400

    try:
        from webapp.helpers.openai_helper import OpenAIHelper
        helper = OpenAIHelper(base_url=base_url, api_key=api_key)
        models = helper.list_models()
        if not models:
            return jsonify({'error': '無法取得模型列表，請確認 URL 和 API Key'}), 400
        return jsonify(models)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: 確認 `settings.py` 的 test endpoint 支援 openai provider**

找到 `api_test_translation_settings()`，確認 provider dispatch 包含 openai：

```python
# 在 test endpoint 的 if/elif chain 中加入：
elif provider == 'openai':
    db_setting = TranslationSetting.query.filter_by(provider='openai').first()
    result = translation_service.translate_with_override(
        test_text, provider, settings_data, db_setting)
```

- [ ] **Step 5: 驗證 probe-models endpoint**

```bash
curl -X POST http://localhost:9000/api/translation-settings/openai/probe-models \
  -H 'Content-Type: application/json' \
  -d '{"base_url":"https://api.openai.com/v1","api_key":""}'
# Expected: 400 (無 key) 或 JSON array of model ids
```

- [ ] **Step 6: Commit**

```bash
git add webapp/models.py webapp/routes/api/settings.py
git commit -m "feat: add OpenAI-compatible translation provider + probe-models endpoint"
```

---

## Phase 5：類別扁平化遷移

### Task 10：遷移腳本 + Admin Endpoint

**Files:**
- Create: `migrate_flatten_categories.py`
- Modify: `webapp/routes/api/settings.py` (加入 admin endpoint)

- [ ] **Step 1: 建立 `migrate_flatten_categories.py`**

```python
# -*- coding: utf-8 -*-
"""
One-time migration: flatten multi-level category tree to single level.

Before: People > Artists > Anime Artists  (name: 'anime_artists', parent_id=<artists_id>)
After:  name: 'people__artists__anime_artists', parent_id=None, level=0

Run:
  flask --app app shell < migrate_flatten_categories.py
  # or POST /api/admin/migrate-flatten
"""

from webapp.models import db, Category


def run_migration():
    all_cats = Category.query.all()
    cat_map = {c.id: c for c in all_cats}

    def full_name(cat):
        parts = [cat.name]
        current = cat
        while current.parent_id and current.parent_id in cat_map:
            current = cat_map[current.parent_id]
            parts.insert(0, current.name)
        return '__'.join(parts)

    # Pre-compute all new names before modifying
    new_names = {c.id: full_name(c) for c in all_cats}

    # Categorise: keep if has wildcards OR is a leaf
    keep_ids = {c.id for c in all_cats if len(c.wildcards) > 0 or len(c.children) == 0}
    delete_ids = {c.id for c in all_cats} - keep_ids

    print(f"Flattening {len(keep_ids)} categories, removing {len(delete_ids)} structural nodes...")

    # Step 1: Detach kept categories from hierarchy (set parent_id=None first)
    for cat_id in keep_ids:
        cat = cat_map[cat_id]
        new_name = new_names[cat_id]
        print(f"  Keep: '{cat.name}' → '{new_name}'")
        cat.name = new_name
        cat.parent_id = None
        cat.level = 0
    db.session.flush()

    # Step 2: Delete structural nodes (no wildcards, no longer have children after step 1)
    for cat_id in delete_ids:
        cat = cat_map[cat_id]
        print(f"  Remove structural: '{cat.name}'")
        # Use direct delete to bypass cascade issues
        db.session.execute(
            db.text('DELETE FROM categories WHERE id = :id'),
            {'id': cat_id}
        )

    db.session.commit()
    remaining = Category.query.count()
    print(f"\n✓ Migration complete. Categories remaining: {remaining}")
    return {'kept': len(keep_ids), 'removed': len(delete_ids)}


if __name__ == '__main__':
    # For direct execution: python migrate_flatten_categories.py
    from webapp import create_app
    with create_app().app_context():
        run_migration()
```

- [ ] **Step 2: 在 `settings.py` 加入 admin endpoint**

```python
@settings_bp.route('/admin/migrate-flatten', methods=['POST'])
def api_migrate_flatten():
    """One-time: flatten multi-level category tree to single level.
    Safe to call multiple times (idempotent after first run).
    """
    try:
        from migrate_flatten_categories import run_migration
        result = run_migration()
        return jsonify({'message': '扁平化遷移完成', **result})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 3: 驗證腳本（測試模式）**

```bash
# 先備份資料庫（如使用 SQLite）
cp data/wildcard.db data/wildcard.db.bak

# 驗證腳本可以 import 和執行
python migrate_flatten_categories.py
# Expected: 列出每個分類的轉換，最後顯示 "✓ Migration complete."
```

- [ ] **Step 4: 確認分類結構**

```bash
curl http://localhost:9000/api/categories
# Expected: all categories have parent_id=null, level=0
# names like "people__artists__anime_artists"
```

- [ ] **Step 5: Commit**

```bash
git add migrate_flatten_categories.py webapp/routes/api/settings.py
git commit -m "feat: add category flattening migration script + admin endpoint"
```

---

## Phase 6：UI 更新

### Task 11：首頁簡化

**Files:**
- Modify: `webapp/templates/index.html`
- Modify: `webapp/routes/api/settings.py` (`/api/stats` 回傳不含 category_stats)

- [ ] **Step 1: 更新 `api_stats` — 移除 category_stats**

在 `settings.py` 找到 `api_stats()` 路由，將回傳改為：

```python
@settings_bp.route('/stats', methods=['GET'])
def api_stats():
    total_wildcards = Wildcard.query.count()
    active_wildcards = Wildcard.query.filter_by(is_active=True).count()
    total_categories = Category.query.count()
    return jsonify({
        'total_wildcards': total_wildcards,
        'active_wildcards': active_wildcards,
        'inactive_wildcards': total_wildcards - active_wildcards,
        'total_categories': total_categories,
    })
```

- [ ] **Step 2: 重寫 `webapp/templates/index.html`**

```html
{% extends "base.html" %}
{% block title %}首頁 - Wildcard 管理系統{% endblock %}

{% block content %}
<div class="container-fluid">
  <div class="d-flex justify-content-between align-items-center mb-4">
    <h2><i class="bi bi-stars"></i> Wildcard 管理系統</h2>
  </div>

  <!-- Stats Cards -->
  <div class="row mb-4" id="statsCards">
    <div class="col-md-4">
      <div class="card text-center border-primary">
        <div class="card-body">
          <div class="display-4 fw-bold text-primary" id="totalWildcards">—</div>
          <div class="text-muted">總 Wildcard 數</div>
        </div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card text-center border-success">
        <div class="card-body">
          <div class="display-4 fw-bold text-success" id="activeWildcards">—</div>
          <div class="text-muted">已啟用</div>
        </div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card text-center border-info">
        <div class="card-body">
          <div class="display-4 fw-bold text-info" id="totalCategories">—</div>
          <div class="text-muted">分類數</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Quick Links -->
  <div class="row g-3">
    <div class="col-6 col-md-3">
      <a href="/wildcards" class="btn btn-outline-primary w-100 py-3">
        <i class="bi bi-list-ul d-block fs-3 mb-1"></i> Wildcard 管理
      </a>
    </div>
    <div class="col-6 col-md-3">
      <a href="/import" class="btn btn-outline-secondary w-100 py-3">
        <i class="bi bi-upload d-block fs-3 mb-1"></i> 匯入資料
      </a>
    </div>
    <div class="col-6 col-md-3">
      <a href="/export" class="btn btn-outline-secondary w-100 py-3">
        <i class="bi bi-download d-block fs-3 mb-1"></i> 匯出資料
      </a>
    </div>
    <div class="col-6 col-md-3">
      <a href="/translation-settings" class="btn btn-outline-secondary w-100 py-3">
        <i class="bi bi-gear-fill d-block fs-3 mb-1"></i> 翻譯設定
      </a>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
fetch('/api/stats').then(r => r.json()).then(data => {
  document.getElementById('totalWildcards').textContent = data.total_wildcards.toLocaleString();
  document.getElementById('activeWildcards').textContent = data.active_wildcards.toLocaleString();
  document.getElementById('totalCategories').textContent = data.total_categories.toLocaleString();
});
</script>
{% endblock %}
```

- [ ] **Step 3: 驗證首頁**

瀏覽 `http://localhost:9000`，確認三個數字正確載入，無舊的 category 圖表。

- [ ] **Step 4: Commit**

```bash
git add webapp/templates/index.html webapp/routes/api/settings.py
git commit -m "ui: simplify homepage - remove category stats chart, add quick links"
```

---

### Task 12：翻譯設定頁面改版

**Files:**
- Modify: `webapp/templates/translation_settings.html`

- [ ] **Step 1: 重寫 `webapp/templates/translation_settings.html`**

移除 Pollinations tab，新增 OpenAI-compatible tab：

```html
{% extends "base.html" %}
{% block title %}翻譯設定 - Wildcard 管理系統{% endblock %}

{% block extra_css %}
<style>
  .font-monospace { font-family: 'Courier New', Courier, monospace; }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid">
  <div class="d-flex justify-content-between align-items-center mb-4">
    <h2><i class="bi bi-gear-fill"></i> 翻譯設定</h2>
  </div>

  <!-- Active Provider Selector -->
  <div class="card mb-4">
    <div class="card-header"><h5 class="mb-0"><i class="bi bi-power"></i> 啟用中的翻譯服務</h5></div>
    <div class="card-body d-flex align-items-center gap-3">
      <select id="activeProvider" class="form-select w-auto"></select>
      <div id="activationStatus" class="text-muted small"></div>
    </div>
  </div>

  <!-- Provider Tabs -->
  <ul class="nav nav-tabs" id="providerTabs">
    <li class="nav-item">
      <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#ollama-pane">
        <i class="bi bi-hdd-stack"></i> Ollama
      </button>
    </li>
    <li class="nav-item">
      <button class="nav-link" data-bs-toggle="tab" data-bs-target="#gemini-pane">
        <i class="bi bi-gem"></i> Google Gemini
      </button>
    </li>
    <li class="nav-item">
      <button class="nav-link" data-bs-toggle="tab" data-bs-target="#openai-pane">
        <i class="bi bi-cpu"></i> OpenAI-compatible
      </button>
    </li>
  </ul>

  <div class="tab-content">
    <!-- Ollama -->
    <div class="tab-pane fade show active" id="ollama-pane">
      <div class="card card-body border-top-0">
        <form id="ollamaForm" data-provider="ollama">
          <div class="mb-3">
            <label class="form-label">模型名稱</label>
            <input type="text" class="form-control" id="ollama-modelName" required>
            <div class="form-text">例如: qwen3:8b, llama3</div>
          </div>
          <div class="mb-3">
            <label class="form-label">溫度 (<span class="temp-val">0.3</span>)</label>
            <input type="range" class="form-range temp-slider" id="ollama-temperature" min="0" max="2" step="0.1">
          </div>
          <div class="mb-3">
            <label class="form-label">系統提示詞</label>
            <textarea class="form-control font-monospace" id="ollama-systemPrompt" rows="8"></textarea>
          </div>
          <button type="submit" class="btn btn-primary"><i class="bi bi-save"></i> 儲存</button>
        </form>
      </div>
    </div>

    <!-- Gemini -->
    <div class="tab-pane fade" id="gemini-pane">
      <div class="card card-body border-top-0">
        <form id="geminiForm" data-provider="gemini">
          <div class="mb-3">
            <label class="form-label">API 金鑰</label>
            <input type="password" class="form-control" id="gemini-apiKey" placeholder="留空 = 不更新">
          </div>
          <div class="mb-3">
            <label class="form-label">模型名稱</label>
            <input type="text" class="form-control" id="gemini-modelName" required>
          </div>
          <div class="mb-3">
            <label class="form-label">溫度 (<span class="temp-val">0.3</span>)</label>
            <input type="range" class="form-range temp-slider" id="gemini-temperature" min="0" max="1" step="0.1">
          </div>
          <div class="mb-3">
            <label class="form-label">系統提示詞</label>
            <textarea class="form-control font-monospace" id="gemini-systemPrompt" rows="8"></textarea>
          </div>
          <button type="submit" class="btn btn-primary"><i class="bi bi-save"></i> 儲存</button>
        </form>
      </div>
    </div>

    <!-- OpenAI-compatible -->
    <div class="tab-pane fade" id="openai-pane">
      <div class="card card-body border-top-0">
        <form id="openaiForm" data-provider="openai">
          <div class="mb-3">
            <label class="form-label">Base URL</label>
            <input type="url" class="form-control" id="openai-baseUrl"
                   placeholder="https://api.openai.com/v1">
            <div class="form-text">本地服務範例：http://localhost:1234/v1（LM Studio）、http://localhost:11434/v1（Ollama）</div>
          </div>
          <div class="mb-3">
            <label class="form-label">API Key</label>
            <input type="password" class="form-control" id="openai-apiKey"
                   placeholder="留空 = 無鑑權模式（相容本地服務）">
          </div>
          <div class="mb-3">
            <label class="form-label">模型</label>
            <div class="input-group">
              <select class="form-select" id="openai-modelName">
                <option value="">先儲存 Base URL 再掃描，或直接輸入</option>
              </select>
              <input type="text" class="form-control" id="openai-modelNameInput"
                     placeholder="手動輸入模型名稱" style="display:none">
              <button type="button" class="btn btn-outline-secondary" id="probeModelsBtn">
                <i class="bi bi-search"></i> 掃描可用模型
              </button>
            </div>
            <div id="probeStatus" class="form-text mt-1"></div>
          </div>
          <div class="mb-3">
            <label class="form-label">溫度 (<span class="temp-val">0.3</span>)</label>
            <input type="range" class="form-range temp-slider" id="openai-temperature" min="0" max="2" step="0.1">
          </div>
          <div class="mb-3">
            <label class="form-label">系統提示詞</label>
            <textarea class="form-control font-monospace" id="openai-systemPrompt" rows="8"></textarea>
          </div>
          <button type="submit" class="btn btn-primary"><i class="bi bi-save"></i> 儲存 OpenAI 設定</button>
        </form>
      </div>
    </div>
  </div>

  <!-- Test Area -->
  <div class="card mt-4">
    <div class="card-header bg-success text-white"><h5 class="mb-0"><i class="bi bi-play-circle"></i> 測試當前設定</h5></div>
    <div class="card-body">
      <div class="mb-3">
        <input type="text" class="form-control" id="testText" value="a beautiful cat with blue eyes">
      </div>
      <button type="button" class="btn btn-success" id="testBtn"><i class="bi bi-play-fill"></i> 測試翻譯</button>
      <div id="testResult" class="alert alert-info mt-3 d-none"></div>
      <div id="testError" class="alert alert-danger mt-3 d-none"></div>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', () => {
  const PROVIDERS = ['ollama', 'gemini', 'openai'];

  // --- Temperature sliders ---
  document.querySelectorAll('.temp-slider').forEach(slider => {
    slider.addEventListener('input', e => {
      e.target.closest('.mb-3').querySelector('.temp-val').textContent = e.target.value;
    });
  });

  // --- Load settings ---
  async function loadSettings() {
    const resp = await fetch('/api/translation-settings');
    const list = await resp.json();
    const sel = document.getElementById('activeProvider');
    sel.innerHTML = '';
    let active = null;

    list.forEach(s => {
      if (!PROVIDERS.includes(s.provider)) return;
      sel.add(new Option(s.provider.toUpperCase(), s.provider));
      if (s.is_active) active = s.provider;

      // Fill form fields
      const prefix = s.provider;
      const modelEl = document.getElementById(`${prefix}-modelName`);
      if (modelEl) modelEl.value = s.model_name || '';

      const tempEl = document.getElementById(`${prefix}-temperature`);
      if (tempEl) {
        tempEl.value = s.temperature;
        tempEl.closest('.mb-3').querySelector('.temp-val').textContent = s.temperature;
      }

      const promptEl = document.getElementById(`${prefix}-systemPrompt`);
      if (promptEl) promptEl.value = s.system_prompt || '';

      if (s.provider === 'openai') {
        document.getElementById('openai-baseUrl').value = s.base_url || '';
      }
    });

    if (active) sel.value = active;
  }

  // --- Save forms ---
  async function saveForm(e) {
    e.preventDefault();
    const provider = e.target.dataset.provider;
    const body = {
      model_name: document.getElementById(`${provider}-modelName`)?.value
                  || document.getElementById('openai-modelNameInput')?.value || '',
      temperature: parseFloat(document.getElementById(`${provider}-temperature`).value),
      system_prompt: document.getElementById(`${provider}-systemPrompt`).value,
    };
    if (provider === 'gemini') {
      const key = document.getElementById('gemini-apiKey').value;
      if (key) body.api_key = key;
    }
    if (provider === 'openai') {
      body.base_url = document.getElementById('openai-baseUrl').value;
      const key = document.getElementById('openai-apiKey').value;
      if (key) body.api_key = key;
      // Use select value or manual input
      body.model_name = document.getElementById('openai-modelName').value
                        || document.getElementById('openai-modelNameInput').value;
    }
    const resp = await fetch(`/api/translation-settings/${provider}`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    if (resp.ok) {
      alert(`${provider.toUpperCase()} 設定已儲存！`);
      if (provider === 'gemini') document.getElementById('gemini-apiKey').value = '';
      if (provider === 'openai') document.getElementById('openai-apiKey').value = '';
    } else {
      const err = await resp.json();
      alert(`儲存失敗: ${err.error}`);
    }
  }

  document.querySelectorAll('form[data-provider]').forEach(f => f.addEventListener('submit', saveForm));

  // --- Active provider switch ---
  document.getElementById('activeProvider').addEventListener('change', async e => {
    const status = document.getElementById('activationStatus');
    status.textContent = '切換中...';
    const resp = await fetch('/api/translation-settings/activate', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({provider: e.target.value})
    });
    const r = await resp.json();
    status.textContent = resp.ok ? r.message : `錯誤: ${r.error}`;
  });

  // --- Probe Models ---
  document.getElementById('probeModelsBtn').addEventListener('click', async () => {
    const baseUrl = document.getElementById('openai-baseUrl').value.trim();
    const apiKey = document.getElementById('openai-apiKey').value.trim();
    const status = document.getElementById('probeStatus');
    const modelSel = document.getElementById('openai-modelName');

    if (!baseUrl) { status.textContent = '請先填入 Base URL'; return; }

    status.textContent = '掃描中...';
    try {
      const resp = await fetch('/api/translation-settings/openai/probe-models', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({base_url: baseUrl, api_key: apiKey})
      });
      if (!resp.ok) {
        const err = await resp.json();
        status.textContent = `❌ ${err.error}`;
        return;
      }
      const models = await resp.json();
      modelSel.innerHTML = models.map(m => `<option value="${m}">${m}</option>`).join('');
      status.textContent = `✓ 找到 ${models.length} 個模型`;
    } catch (e) {
      status.textContent = `❌ 連線失敗: ${e.message}`;
    }
  });

  // --- Test Translation ---
  document.getElementById('testBtn').addEventListener('click', async () => {
    const text = document.getElementById('testText').value.trim();
    if (!text) return;

    const activeTab = document.querySelector('.tab-pane.active');
    const provider = activeTab.id.replace('-pane', '');
    const settings = {
      model_name: document.getElementById(`${provider}-modelName`)?.value || '',
      temperature: parseFloat(document.getElementById(`${provider}-temperature`).value),
      system_prompt: document.getElementById(`${provider}-systemPrompt`).value,
    };
    if (provider === 'openai') {
      settings.base_url = document.getElementById('openai-baseUrl').value;
      settings.model_name = document.getElementById('openai-modelName').value
                            || document.getElementById('openai-modelNameInput').value;
    }

    const resultEl = document.getElementById('testResult');
    const errorEl = document.getElementById('testError');
    resultEl.classList.add('d-none');
    errorEl.classList.add('d-none');

    const resp = await fetch('/api/translation-settings/test', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, provider, settings})
    });
    const r = await resp.json();
    if (resp.ok) {
      resultEl.innerHTML = `<strong>原文:</strong> ${r.original}<br>
        <strong>譯文:</strong> <span class="fw-bold text-primary">${r.translated}</span>`;
      resultEl.classList.remove('d-none');
    } else {
      errorEl.textContent = `測試失敗: ${r.error}`;
      errorEl.classList.remove('d-none');
    }
  });

  loadSettings();
});
</script>
{% endblock %}
```

- [ ] **Step 2: 驗證翻譯設定頁**

瀏覽 `http://localhost:9000/translation-settings`：
- 確認只有 Ollama / Gemini / OpenAI-compatible 三個 tab
- 無 Pollinations tab
- OpenAI tab 的「掃描可用模型」按鈕可點擊（填入有效 URL 後）

- [ ] **Step 3: Commit**

```bash
git add webapp/templates/translation_settings.html
git commit -m "ui: redesign translation settings - remove Pollinations, add OpenAI-compatible tab"
```

---

### Task 13：整合 Wildcards + Categories 頁面 + Navbar 更新

**Files:**
- Modify: `webapp/templates/wildcards.html` (完整重寫)
- Modify: `webapp/templates/base.html` (移除類別管理連結)
- Delete: `webapp/templates/categories.html`

- [ ] **Step 1: 更新 `webapp/templates/base.html` navbar**

找到「類別管理」的 `<li class="nav-item">` 區塊，整個刪除：

```html
<!-- 刪除這整個 li -->
<li class="nav-item">
    <a class="nav-link" href="/categories">
        <i class="bi bi-folder"></i> 類別管理
    </a>
</li>
```

同時將「Wildcard 列表」連結的文字改為「Wildcard 管理」：

```html
<a class="nav-link" href="/wildcards">
    <i class="bi bi-list-ul"></i> Wildcard 管理
</a>
```

- [ ] **Step 2: 重寫 `webapp/templates/wildcards.html`**

```html
{% extends "base.html" %}
{% block title %}Wildcard 管理{% endblock %}

{% block extra_css %}
<style>
  #categoryList { max-height: calc(100vh - 220px); overflow-y: auto; }
  #wildcardTable { max-height: calc(100vh - 260px); overflow-y: auto; }
  .category-item { cursor: pointer; padding: 0.4rem 0.75rem; border-radius: 4px; }
  .category-item:hover { background: #f0f0f0; }
  .category-item.active { background: #0d6efd; color: #fff; }
  .category-item.active .badge { background: rgba(255,255,255,0.3) !important; }
  .wildcard-row td { vertical-align: middle; }
  .zh-text { color: #6c757d; font-size: 0.85em; }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid">
  <div class="row" style="height: calc(100vh - 80px);">

    <!-- Left Panel: Categories -->
    <div class="col-3 border-end pe-0 d-flex flex-column">
      <div class="p-3 border-bottom">
        <div class="d-flex gap-2 mb-2">
          <button class="btn btn-sm btn-primary flex-grow-1" id="addCategoryBtn">
            <i class="bi bi-plus-lg"></i> 新增分類
          </button>
        </div>
        <div id="newCategoryForm" class="d-none">
          <div class="input-group input-group-sm">
            <input type="text" class="form-control" id="newCategoryName"
                   placeholder="分類名稱（英文，用_分隔）">
            <button class="btn btn-success" id="saveCategoryBtn"><i class="bi bi-check"></i></button>
            <button class="btn btn-secondary" id="cancelCategoryBtn"><i class="bi bi-x"></i></button>
          </div>
          <input type="text" class="form-control form-control-sm mt-1" id="newCategoryDisplayName"
                 placeholder="顯示名稱（中文）">
        </div>
        <input type="text" class="form-control form-control-sm mt-2" id="categorySearch"
               placeholder="🔍 搜尋分類...">
      </div>
      <div id="categoryList" class="p-2 flex-grow-1">
        <div class="text-muted text-center py-3">載入中...</div>
      </div>
      <div class="p-2 border-top bg-light" id="selectedCategoryActions" style="display:none!important">
        <small class="text-muted d-block mb-1" id="selectedCategoryName"></small>
        <div class="d-flex gap-1">
          <button class="btn btn-sm btn-outline-secondary flex-grow-1" id="renameCategoryBtn">
            <i class="bi bi-pencil"></i> 改名
          </button>
          <button class="btn btn-sm btn-outline-danger flex-grow-1" id="deleteCategoryBtn">
            <i class="bi bi-trash"></i> 刪除
          </button>
        </div>
      </div>
    </div>

    <!-- Right Panel: Wildcards -->
    <div class="col-9 d-flex flex-column ps-0">
      <div class="p-3 border-bottom">
        <div class="d-flex gap-2 flex-wrap align-items-center">
          <input type="text" class="form-control form-control-sm" id="wildcardSearch"
                 placeholder="🔍 搜尋 wildcard..." style="max-width:220px">
          <select class="form-select form-select-sm" id="statusFilter" style="max-width:120px">
            <option value="">全部狀態</option>
            <option value="true">啟用</option>
            <option value="false">停用</option>
          </select>
          <div class="ms-auto d-flex gap-2">
            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">
              批量操作
            </button>
            <ul class="dropdown-menu">
              <li><a class="dropdown-item" href="#" id="batchEnableBtn">批量啟用</a></li>
              <li><a class="dropdown-item" href="#" id="batchDisableBtn">批量停用</a></li>
              <li><a class="dropdown-item" href="#" id="batchTranslateBtn">批量翻譯</a></li>
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item text-danger" href="#" id="batchDeleteBtn">批量刪除</a></li>
            </ul>
            <button class="btn btn-sm btn-primary" id="addWildcardBtn">
              <i class="bi bi-plus-lg"></i> 新增
            </button>
          </div>
        </div>
        <div class="d-flex align-items-center mt-2 gap-2">
          <div class="form-check mb-0">
            <input class="form-check-input" type="checkbox" id="selectAll">
            <label class="form-check-label small" for="selectAll">全選</label>
          </div>
          <small class="text-muted" id="selectionInfo">請選擇分類</small>
        </div>
      </div>

      <div id="wildcardTable" class="flex-grow-1 overflow-auto">
        <table class="table table-hover table-sm mb-0">
          <tbody id="wildcardBody">
            <tr><td colspan="4" class="text-center text-muted py-4">← 請選擇分類</td></tr>
          </tbody>
        </table>
      </div>

      <div class="p-2 border-top d-flex justify-content-between align-items-center">
        <small class="text-muted" id="paginationInfo"></small>
        <div id="paginationControls" class="d-flex gap-1"></div>
      </div>
    </div>
  </div>
</div>

<!-- Edit Wildcard Modal -->
<div class="modal fade" id="editModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">編輯 Wildcard</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="editId">
        <div class="mb-3">
          <label class="form-label">英文內容</label>
          <input type="text" class="form-control" id="editContent">
        </div>
        <div class="mb-3">
          <label class="form-label">中文翻譯</label>
          <input type="text" class="form-control" id="editContentZh">
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
        <button type="button" class="btn btn-primary" id="saveEditBtn">儲存</button>
      </div>
    </div>
  </div>
</div>

<!-- Add Wildcard Modal -->
<div class="modal fade" id="addWildcardModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">新增 Wildcard</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <div class="mb-3">
          <label class="form-label">英文內容（每行一個）</label>
          <textarea class="form-control" id="newWildcardContent" rows="6"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
        <button type="button" class="btn btn-primary" id="saveNewWildcardBtn">新增</button>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', () => {
  // --- State ---
  let selectedCategoryId = null;
  let selectedCategoryName = '';
  let currentPage = 1;
  let totalPages = 1;
  let searchTimeout = null;

  // --- Category Panel ---
  async function loadCategories() {
    const search = document.getElementById('categorySearch').value.toLowerCase();
    const resp = await fetch('/api/categories');
    const cats = await resp.json();
    const list = document.getElementById('categoryList');
    const filtered = cats.filter(c =>
      c.name.toLowerCase().includes(search) ||
      c.display_name.toLowerCase().includes(search)
    );
    if (!filtered.length) {
      list.innerHTML = '<div class="text-muted text-center py-3">無分類</div>';
      return;
    }
    list.innerHTML = filtered.map(c => `
      <div class="category-item d-flex justify-content-between align-items-center
                  ${c.id === selectedCategoryId ? 'active' : ''}"
           data-id="${c.id}" data-name="${c.name}" data-display="${c.display_name}">
        <span class="text-truncate">${c.display_name || c.name}</span>
        <span class="badge bg-secondary ms-1">${c.wildcard_count ?? ''}</span>
      </div>
    `).join('');
    list.querySelectorAll('.category-item').forEach(el => {
      el.addEventListener('click', () => selectCategory(
        parseInt(el.dataset.id), el.dataset.name, el.dataset.display
      ));
    });
  }

  function selectCategory(id, name, display) {
    selectedCategoryId = id;
    selectedCategoryName = name;
    currentPage = 1;
    document.getElementById('wildcardSearch').value = '';
    document.getElementById('statusFilter').value = '';
    const actionsEl = document.getElementById('selectedCategoryActions');
    actionsEl.style.setProperty('display', 'block', 'important');
    document.getElementById('selectedCategoryName').textContent = display || name;
    loadCategories();
    loadWildcards();
  }

  document.getElementById('categorySearch').addEventListener('input', () => loadCategories());

  // Add category
  document.getElementById('addCategoryBtn').addEventListener('click', () => {
    document.getElementById('newCategoryForm').classList.toggle('d-none');
  });
  document.getElementById('cancelCategoryBtn').addEventListener('click', () => {
    document.getElementById('newCategoryForm').classList.add('d-none');
  });
  document.getElementById('saveCategoryBtn').addEventListener('click', async () => {
    const name = document.getElementById('newCategoryName').value.trim();
    const display = document.getElementById('newCategoryDisplayName').value.trim();
    if (!name) return;
    await fetch('/api/categories', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, display_name: display || name})
    });
    document.getElementById('newCategoryName').value = '';
    document.getElementById('newCategoryDisplayName').value = '';
    document.getElementById('newCategoryForm').classList.add('d-none');
    loadCategories();
  });

  // Rename category
  document.getElementById('renameCategoryBtn').addEventListener('click', async () => {
    const newDisplay = prompt('新的顯示名稱:', selectedCategoryName);
    if (!newDisplay) return;
    await fetch(`/api/categories/${selectedCategoryId}`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({display_name: newDisplay})
    });
    loadCategories();
  });

  // Delete category
  document.getElementById('deleteCategoryBtn').addEventListener('click', async () => {
    if (!confirm(`確定刪除分類「${selectedCategoryName}」及其所有 wildcard？`)) return;
    await fetch(`/api/categories/${selectedCategoryId}`, {method: 'DELETE'});
    selectedCategoryId = null;
    document.getElementById('selectedCategoryActions').style.setProperty('display', 'none', 'important');
    document.getElementById('wildcardBody').innerHTML =
      '<tr><td colspan="4" class="text-center text-muted py-4">← 請選擇分類</td></tr>';
    loadCategories();
  });

  // --- Wildcard Panel ---
  async function loadWildcards() {
    if (!selectedCategoryId) return;
    const search = document.getElementById('wildcardSearch').value;
    const status = document.getElementById('statusFilter').value;
    const params = new URLSearchParams({
      category_id: selectedCategoryId,
      page: currentPage,
      per_page: 50,
    });
    if (search) params.set('search', search);
    if (status !== '') params.set('is_active', status);

    const resp = await fetch('/api/wildcards?' + params);
    const data = await resp.json();
    totalPages = data.pages || 1;
    renderWildcards(data.items);
    renderPagination(data.total);
    document.getElementById('selectionInfo').textContent =
      `共 ${data.total} 筆（第 ${currentPage}/${totalPages} 頁）`;
  }

  function renderWildcards(items) {
    const body = document.getElementById('wildcardBody');
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">此分類無 wildcard</td></tr>';
      return;
    }
    body.innerHTML = items.map(w => `
      <tr class="wildcard-row" data-id="${w.id}">
        <td style="width:32px">
          <input class="form-check-input row-check" type="checkbox" value="${w.id}">
        </td>
        <td>
          <div>${escHtml(w.content)}</div>
          ${w.content_zh ? `<div class="zh-text">${escHtml(w.content_zh)}</div>` : ''}
        </td>
        <td style="width:80px">
          <div class="form-check form-switch mb-0">
            <input class="form-check-input active-toggle" type="checkbox"
                   data-id="${w.id}" ${w.is_active ? 'checked' : ''}>
          </div>
        </td>
        <td style="width:60px">
          <div class="dropdown">
            <button class="btn btn-sm btn-link text-muted" data-bs-toggle="dropdown">⋯</button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li><a class="dropdown-item edit-btn" href="#" data-id="${w.id}"
                     data-content="${escHtml(w.content)}"
                     data-zh="${escHtml(w.content_zh || '')}">編輯</a></li>
              <li><a class="dropdown-item translate-one-btn" href="#"
                     data-id="${w.id}">翻譯此項</a></li>
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item text-danger delete-one-btn" href="#"
                     data-id="${w.id}">刪除</a></li>
            </ul>
          </div>
        </td>
      </tr>
    `).join('');

    // Toggle active
    body.querySelectorAll('.active-toggle').forEach(cb => {
      cb.addEventListener('change', async e => {
        await fetch(`/api/wildcards/${e.target.dataset.id}`, {
          method: 'PUT', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({is_active: e.target.checked})
        });
      });
    });

    // Edit
    body.querySelectorAll('.edit-btn').forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        document.getElementById('editId').value = btn.dataset.id;
        document.getElementById('editContent').value = btn.dataset.content;
        document.getElementById('editContentZh').value = btn.dataset.zh;
        new bootstrap.Modal(document.getElementById('editModal')).show();
      });
    });

    // Translate one
    body.querySelectorAll('.translate-one-btn').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.preventDefault();
        await fetch('/api/wildcards/batch-translate', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ids: [parseInt(btn.dataset.id)]})
        });
        loadWildcards();
      });
    });

    // Delete one
    body.querySelectorAll('.delete-one-btn').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.preventDefault();
        if (!confirm('確定刪除？')) return;
        await fetch(`/api/wildcards/${btn.dataset.id}`, {method: 'DELETE'});
        loadWildcards();
      });
    });
  }

  function renderPagination(total) {
    const ctrl = document.getElementById('paginationControls');
    if (totalPages <= 1) { ctrl.innerHTML = ''; return; }
    const pages = [];
    for (let i = 1; i <= totalPages; i++) {
      pages.push(`<button class="btn btn-sm ${i === currentPage ? 'btn-primary' : 'btn-outline-secondary'}"
        onclick="goPage(${i})">${i}</button>`);
    }
    ctrl.innerHTML = pages.join('');
  }

  window.goPage = function(page) {
    currentPage = page;
    loadWildcards();
  };

  // Search debounce
  document.getElementById('wildcardSearch').addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { currentPage = 1; loadWildcards(); }, 300);
  });
  document.getElementById('statusFilter').addEventListener('change', () => {
    currentPage = 1; loadWildcards();
  });

  // Select all
  document.getElementById('selectAll').addEventListener('change', e => {
    document.querySelectorAll('.row-check').forEach(cb => cb.checked = e.target.checked);
  });

  function getSelectedIds() {
    return [...document.querySelectorAll('.row-check:checked')].map(cb => parseInt(cb.value));
  }

  // Batch ops
  document.getElementById('batchEnableBtn').addEventListener('click', async e => {
    e.preventDefault();
    const ids = getSelectedIds();
    if (!ids.length) { alert('請先選取項目'); return; }
    await fetch('/api/wildcards/batch-update-active', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ids, is_active: true})
    });
    loadWildcards();
  });
  document.getElementById('batchDisableBtn').addEventListener('click', async e => {
    e.preventDefault();
    const ids = getSelectedIds();
    if (!ids.length) { alert('請先選取項目'); return; }
    await fetch('/api/wildcards/batch-update-active', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ids, is_active: false})
    });
    loadWildcards();
  });
  document.getElementById('batchTranslateBtn').addEventListener('click', async e => {
    e.preventDefault();
    const ids = getSelectedIds();
    if (!ids.length) { alert('請先選取項目'); return; }
    document.getElementById('selectionInfo').textContent = '翻譯中...';
    await fetch('/api/wildcards/batch-translate', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ids})
    });
    loadWildcards();
  });
  document.getElementById('batchDeleteBtn').addEventListener('click', async e => {
    e.preventDefault();
    const ids = getSelectedIds();
    if (!ids.length) { alert('請先選取項目'); return; }
    if (!confirm(`確定刪除選取的 ${ids.length} 個 wildcard？`)) return;
    await fetch('/api/wildcards/batch-delete', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ids})
    });
    loadWildcards();
  });

  // Save edit
  document.getElementById('saveEditBtn').addEventListener('click', async () => {
    const id = document.getElementById('editId').value;
    await fetch(`/api/wildcards/${id}`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        content: document.getElementById('editContent').value,
        content_zh: document.getElementById('editContentZh').value,
      })
    });
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
    loadWildcards();
  });

  // Add wildcard
  document.getElementById('addWildcardBtn').addEventListener('click', () => {
    if (!selectedCategoryId) { alert('請先選擇分類'); return; }
    new bootstrap.Modal(document.getElementById('addWildcardModal')).show();
  });
  document.getElementById('saveNewWildcardBtn').addEventListener('click', async () => {
    const lines = document.getElementById('newWildcardContent').value
      .split('\n').map(l => l.trim()).filter(Boolean);
    for (const content of lines) {
      await fetch('/api/wildcards', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content, category_id: selectedCategoryId})
      });
    }
    bootstrap.Modal.getInstance(document.getElementById('addWildcardModal')).hide();
    document.getElementById('newWildcardContent').value = '';
    loadWildcards();
    loadCategories();
  });

  // --- Utilities ---
  function escHtml(str) {
    return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // --- Init ---
  loadCategories();

  // Support URL param ?category_id=
  const urlParams = new URLSearchParams(window.location.search);
  const catId = urlParams.get('category_id');
  if (catId) {
    fetch(`/api/categories/${catId}`).then(r => r.ok ? r.json() : null).then(cat => {
      if (cat) selectCategory(cat.id, cat.name, cat.display_name);
    });
  }
});
</script>
{% endblock %}
```

- [ ] **Step 3: 刪除 `categories.html`（已整合）**

```bash
git rm webapp/templates/categories.html
```

- [ ] **Step 4: 驗證整合頁面**

瀏覽 `http://localhost:9000/wildcards`：
- 左欄顯示分類列表
- 點擊分類 → 右欄顯示 wildcards
- `+ 新增分類` → inline form 出現
- 批量選取 → 批量操作有效
- 翻譯按鈕可用

- [ ] **Step 5: Commit**

```bash
git add webapp/templates/wildcards.html webapp/templates/base.html
git commit -m "ui: integrate wildcard + category management into single dual-panel page"
```

---

## Phase 7：最終驗證與清理

### Task 14：完整系統驗證 + 更新 auto_categorizer.py import

**Files:**
- Modify: `auto_categorizer.py` (更新 helper import 路徑)
- Modify: `bulk_import.py` (更新 helper import 路徑)

- [ ] **Step 1: 更新 `auto_categorizer.py` 的 helper imports**

開啟 `auto_categorizer.py`，找到 `from ollama_helper import OllamaHelper`，改為：

```python
from webapp.helpers.ollama_helper import OllamaHelper
```

- [ ] **Step 2: 更新 `bulk_import.py` 的 helper imports**

開啟 `bulk_import.py`，找到所有根目錄 helper imports，全部改為 `webapp.helpers.*`：

```python
from webapp.helpers.ollama_helper import OllamaHelper
```

- [ ] **Step 3: 執行完整功能驗證清單**

```bash
# API endpoints
curl http://localhost:9000/api/stats
curl http://localhost:9000/api/categories
curl http://localhost:9000/api/wildcards?per_page=5
curl http://localhost:9000/api/translation-settings
curl http://localhost:9000/api/import/history
```

瀏覽器驗證：
- `http://localhost:9000` — 首頁 3 張統計卡片
- `http://localhost:9000/wildcards` — 雙欄整合頁（分類 + wildcards）
- `http://localhost:9000/translation-settings` — 3 個 tab（Ollama/Gemini/OpenAI-compatible）
- `http://localhost:9000/import` — 匯入頁正常
- `http://localhost:9000/export` — 匯出頁正常
- `http://localhost:9000/comfy-monitor` — ComfyUI 監視頁正常
- `http://localhost:9000/prompt-builder` — 提示詞構建器正常

- [ ] **Step 4: 執行類別扁平化遷移**

```bash
curl -X POST http://localhost:9000/api/admin/migrate-flatten
# Expected: {"message":"扁平化遷移完成","kept":N,"removed":M}
```

驗證結果：
```bash
curl http://localhost:9000/api/categories | python -m json.tool | grep parent_id
# Expected: 所有 parent_id 為 null
```

- [ ] **Step 5: Final commit**

```bash
git add auto_categorizer.py bulk_import.py
git commit -m "refactor: update helper import paths in auto_categorizer + bulk_import

Complete app.py refactoring + UI redesign:
- Flask Blueprint + Services architecture
- OpenAI-compatible translation provider
- Removed Pollinations provider
- Integrated wildcard + category management page
- Simplified homepage
- Category flattening migration"
```

---

## 自我審閱

### Spec Coverage
| Spec 需求 | 對應 Task |
|---|---|
| Flask Blueprint + Services | Task 1–8 |
| helpers 移至 webapp/helpers/ | Task 2 |
| Pollinations 移除 | Task 1 (init_data), Task 2 (delete file), Task 12 (UI) |
| OpenAI-compatible provider | Task 2 (helper), Task 9 (endpoint), Task 12 (UI) |
| base_url DB 欄位 | Task 1 (_migrate_schema), Task 9 (to_dict) |
| probe-models endpoint | Task 9 |
| 類別扁平化遷移腳本 | Task 10 |
| 首頁簡化 | Task 11 |
| 翻譯設定頁改版 | Task 12 |
| 整合 Wildcard+Category 頁 | Task 13 |
| Navbar 更新 | Task 13 Step 1 |
| auto_categorizer import 修正 | Task 14 |

### Type Consistency
- `category_service.get_comfy_filepath_for_category()` — 在 wildcard_service 和 comfy_sync Blueprint 中均以相同 signature 使用 ✓
- `translation_service._build_helper()` — 在 translation_service.py 定義並在 settings Blueprint 引用 ✓
- `OpenAIHelper.list_models()` → `list[str]` — 在 translation_service 和 probe-models endpoint 均一致 ✓
- Wildcard 批量操作回傳 `{'updated': int, 'errors': int}` — wildcard_service 定義、wildcards Blueprint 使用 ✓
