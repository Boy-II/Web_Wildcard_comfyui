# -*- coding: utf-8 -*-
"""
Wildcard 管理系統 - 主應用程式
"""

from flask import Flask, render_template, request, jsonify, send_file
from webapp.models import db, Category, Wildcard, ImportHistory, TranslationSetting, AppSetting, PromptTemplate
from ollama_helper import OllamaHelper
from gemini_helper import GeminiHelper
from pollinations_helper import PollinationsHelper
import os
import zipfile
import re
from pathlib import Path
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from werkzeug.utils import secure_filename
import tempfile
import uuid


app = Flask(__name__,
            template_folder='webapp/templates',
            static_folder='webapp/static')
            
# 資料庫設定
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/wildcard.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['OLLAMA_MODEL'] = os.getenv('OLLAMA_MODEL', 'qwen3:8b')
# app.config['COMFYUI_WILDCARD_PATH'] = os.getenv('COMFYUI_WILDCARD_PATH', '/app/comfy_wildcard') # 移除此行，路徑將從資料庫或 get_comfy_wildcard_path 取得

# Ollama URL 設定 (自動偵測 Docker 環境)
in_docker = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
default_ollama_url = "http://host.docker.internal:11434" if in_docker else "http://localhost:11434"
app.config['OLLAMA_BASE_URL'] = os.getenv('OLLAMA_BASE_URL', default_ollama_url)



# 初始化資料庫
db.init_app(app)

def get_comfy_wildcard_path():
    """從資料庫獲取 ComfyUI Wildcard 路徑，如果不存在則從環境變數或預設值"""
    setting = AppSetting.query.filter_by(key='comfyui_wildcard_path').first()
    if setting:
        return setting.value
    # 如果資料庫沒有，則從環境變數獲取
    env_path = os.getenv('COMFYUI_WILDCARD_PATH', '/app/comfy_wildcard')
    return env_path

def init_app_settings():
    """初始化預設應用程式設定"""
    path_setting = AppSetting.query.filter_by(key='comfyui_wildcard_path').first()
    if not path_setting:
        default_path = os.getenv('COMFYUI_WILDCARD_PATH', '/app/comfy_wildcard')
        path_setting = AppSetting(key='comfyui_wildcard_path', value=default_path)
        db.session.add(path_setting)
        db.session.commit()
        print(f"✓ ComfyUI Wildcard 路徑設定初始化完成: {default_path}")
    
    # 設置 app.config 的值以供其他地方使用
    app.config['COMFYUI_WILDCARD_PATH'] = path_setting.value


def init_categories():
    """初始化預設類別 - 從 init_categories.py 載入"""
    # 如果已有分類，不重複初始化
    if Category.query.count() > 0:
        return

    # 匯入分類樹定義
    try:
        from init_categories import CATEGORY_TREE, create_category_tree

        # 創建分類樹
        for root_data in CATEGORY_TREE:
            create_category_tree(root_data)

        db.session.commit()
        print(f"✓ 已初始化 {Category.query.count()} 個分類")
    except Exception as e:
        print(f"初始化分類失敗: {e}")
        db.session.rollback()

def init_translation_settings():
    """初始化預設的翻譯提供者設定"""
    try:
        # 嘗試查詢。如果 schema 不匹配，這裡會拋出錯誤。
        count = TranslationSetting.query.count()
        if count == 0:
            print("初始化翻譯設定...")
            
            # 預設 Ollama 設定
            ollama_settings = TranslationSetting(
                provider='ollama',
                is_active=True,
                model_name='qwen3:8b', # 更正為用戶指定的模型
                temperature=0.3,
                system_prompt="""你是一個專業的AI繪圖提示詞翻譯助手。
你的任務是將英文的AI繪圖提示詞（wildcard）翻譯成簡潔、準確的繁體中文。

翻譯規則：
1. 只返回翻譯結果，不要加任何解釋或額外文字
2. 保持原文的核心含義
3. 對於藝術家名字，保留原文並在括號內註明中文（如果知名）
4. 對於專業術語，使用常見的中文翻譯
5. 保持簡潔，通常不超過原文長度的2倍"""
            )
            db.session.add(ollama_settings)
            
            # 預設 Gemini 設定
            gemini_settings = TranslationSetting(
                provider='gemini',
                is_active=False,
                model_name='models/gemini-flash-latest', # 更換為用戶指定的模型
                temperature=0.3,
                system_prompt="""You are a professional translation assistant for AI drawing prompts.
Your task is to translate English AI drawing prompts (wildcards) into concise and accurate Traditional Chinese.

Translation Rules:
1.  Return only the translated result without any explanation or extra text.
2.  Preserve the core meaning of the original text.
3.  For artist names, keep the original name and note the Chinese name in parentheses if well-known.
4.  Use common Chinese translations for technical terms.
5.  Keep it concise, generally no more than twice the length of the original text."""
            )
            db.session.add(gemini_settings)

            # 預設 Pollinations 設定（完全免費，無需 API key）
            pollinations_settings = TranslationSetting(
                provider='pollinations',
                is_active=False,
                model_name='openai',
                temperature=1.0,
                system_prompt="""你是一個專業的AI繪圖提示詞翻譯助手。
你的任務是將英文的AI繪圖提示詞（wildcard）翻譯成簡潔、準確的繁體中文。

翻譯規則：
1. 只返回翻譯結果，不要加任何解釋或額外文字
2. 保持原文的核心含義
3. 對於藝術家名字，保留原文並在括號內註明中文（如果知名）
4. 對於專業術語，使用常見的中文翻譯
5. 保持簡潔，通常不超過原文長度的2倍"""
            )
            db.session.add(pollinations_settings)

            db.session.commit()
            print("✓ 翻譯設定初始化完成")

    except OperationalError as e:
        print("\n\n" + "="*50)
        print("!!! 資料庫錯誤：偵測到資料庫架構與程式碼不一致。 !!!")
        print("!!! 這通常發生在您更新了程式碼，但仍在使用舊的資料庫磁碟區。")
        print(f"!!! 錯誤詳情: {e}")
        print("!!! 請執行以下指令來徹底清除舊的資料庫並重建：")
        print("!!! 1. docker-compose down -v")
        print("!!! 2. docker-compose up -d --build")
        print("="*50 + "\n\n")
        db.session.rollback()
    except Exception as e:
        print(f"初始化翻譯設定時發生未預期的錯誤: {e}")
        db.session.rollback()

@app.before_request
def create_tables():
    """在第一次請求前建立資料表"""
    if not hasattr(app, 'tables_created'):
        db.create_all()
        init_categories()
        init_translation_settings()
        init_app_settings() # Add this
        app.tables_created = True


# ============= 頁面路由 =============

@app.route('/')
def index():
    """首頁"""
    return render_template('index.html')


@app.route('/categories')
def categories_page():
    """類別管理頁面"""
    return render_template('categories.html')


@app.route('/wildcards')
def wildcards_page():
    """Wildcard 瀏覽頁面"""
    return render_template('wildcards.html')


@app.route('/import')
def import_page():
    """匯入資料頁面"""
    return render_template('import.html')


@app.route('/export')
def export_page():
    """匯出資料頁面"""
    return render_template('export.html')


@app.route('/comfy-monitor')
def comfy_monitor_page():
    """ComfyUI Wildcard 目錄監視頁面"""
    return render_template('comfy_monitor.html')


@app.route('/translation-settings')
def translation_settings_page():
    """翻譯設定頁面"""
    return render_template('translation_settings.html')


@app.route('/prompt-builder')
def prompt_builder_page():
    """提示詞構建器頁面"""
    return render_template('prompt_builder.html')


# ============= API 路由 =============

@app.route('/api/stats')
def api_stats():
    """獲取統計資訊"""
    total_wildcards = Wildcard.query.count()
    active_wildcards = Wildcard.query.filter_by(is_active=True).count()
    total_categories = Category.query.count()

    category_stats = db.session.query(
        Category.name,
        Category.display_name,
        Category.color,
        func.count(Wildcard.id).label('count')
    ).outerjoin(Wildcard).group_by(Category.id).order_by(Category.sort_order).all()

    return jsonify({
        'total_wildcards': total_wildcards,
        'active_wildcards': active_wildcards,
        'inactive_wildcards': total_wildcards - active_wildcards,
        'total_categories': total_categories,
        'category_stats': [
            {
                'name': stat.name,
                'display_name': stat.display_name,
                'color': stat.color,
                'count': stat.count
            }
            for stat in category_stats
        ]
    })


@app.route('/api/categories', methods=['GET'])
def api_get_categories():
    """
    獲取所有類別
    Query參數:
      - tree: true/false - 是否返回樹狀結構（只返回根分類及其子分類）
      - flat: true/false - 返回扁平列表
      - parent_id: int - 只返回特定父分類的子分類
    """
    tree_mode = request.args.get('tree', 'false').lower() == 'true'
    parent_id = request.args.get('parent_id', type=int)

    if parent_id is not None:
        # 返回特定父分類的子分類
        categories = Category.query.filter_by(parent_id=parent_id).order_by(Category.sort_order).all()
        return jsonify([cat.to_dict() for cat in categories])

    if tree_mode:
        # 返回樹狀結構（只返回根分類，子分類嵌套在 children 中）
        root_categories = Category.query.filter_by(parent_id=None).order_by(Category.sort_order).all()
        return jsonify([cat.to_dict(include_children=True) for cat in root_categories])

    # 返回扁平列表
    categories = Category.query.order_by(Category.level, Category.sort_order).all()
    return jsonify([cat.to_dict() for cat in categories])


@app.route('/api/categories', methods=['POST'])
def api_create_category():
    """建立新類別"""
    data = request.json
    
    parent_id = data.get('parent_id')
    level = 0
    if parent_id:
        parent = Category.query.get(parent_id)
        if parent:
            level = parent.level + 1

    category = Category(
        name=data['name'],
        display_name=data['display_name'],
        description=data.get('description'),
        color=data.get('color', '#6c757d'),
        sort_order=data.get('sort_order', 0),
        parent_id=parent_id,
        level=level
    )
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def api_update_category(category_id):
    """更新類別，支援父類別變更和層級遞迴更新"""
    category = Category.query.get_or_404(category_id)
    data = request.json

    category.display_name = data.get('display_name', category.display_name)
    category.description = data.get('description', category.description)
    category.color = data.get('color', category.color)
    category.sort_order = data.get('sort_order', category.sort_order)

    # 處理父類別變更
    if 'parent_id' in data and category.parent_id != data['parent_id']:
        new_parent_id = data.get('parent_id')

        # 簡單的循環依賴檢查
        temp_parent = Category.query.get(new_parent_id) if new_parent_id else None
        while temp_parent is not None:
            if temp_parent.id == category.id:
                return jsonify({'error': '不能將類別設定為自己的子類別'}), 400
            temp_parent = temp_parent.parent

        category.parent_id = new_parent_id
        
        # 遞迴更新層級
        def update_levels_recursively(cat, new_level):
            cat.level = new_level
            for child in cat.children:
                update_levels_recursively(child, new_level + 1)

        parent_level = Category.query.get(new_parent_id).level if new_parent_id else -1
        update_levels_recursively(category, parent_level + 1)

    db.session.commit()
    return jsonify(category.to_dict())


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def api_delete_category(category_id):
    """刪除類別（級聯刪除所有 wildcard 和子類別）"""
    category = Category.query.get_or_404(category_id)

    # 統計即將被刪除的項目
    def count_descendants(cat):
        """遞迴計算子類別和 wildcard 數量"""
        wildcard_count = len(cat.wildcards)
        child_count = len(cat.children)

        for child in cat.children:
            child_wildcards, child_categories = count_descendants(child)
            wildcard_count += child_wildcards
            child_count += child_categories

        return wildcard_count, child_count

    wildcards_to_delete, children_to_delete = count_descendants(category)

    # 在刪除前，處理 ComfyUI 檔案同步（移除啟用的 wildcard）
    comfy_path_str = get_comfy_wildcard_path()
    if comfy_path_str:
        def delete_wildcards_from_comfy(cat):
            """遞迴處理所有子類別的 wildcard 檔案同步"""
            # 處理當前類別的 wildcards
            for wildcard in cat.wildcards:
                if wildcard.is_active:
                    try:
                        dir_path, filename = get_comfy_filepath_for_category(cat, comfy_path_str)
                        filepath = dir_path / filename

                        if filepath.exists():
                            # 從檔案中移除該行
                            with open(filepath, 'r', encoding='utf-8') as f:
                                lines = f.readlines()

                            with open(filepath, 'w', encoding='utf-8') as f:
                                for line in lines:
                                    if line.strip() != wildcard.content:
                                        f.write(line)
                    except Exception as e:
                        print(f"移除 wildcard 檔案同步失敗: {e}")

            # 遞迴處理子類別
            for child in cat.children:
                delete_wildcards_from_comfy(child)

        delete_wildcards_from_comfy(category)

    # 刪除類別（會級聯刪除所有 wildcard 和子類別）
    db.session.delete(category)
    db.session.commit()

    return jsonify({
        'message': '類別已刪除',
        'deleted_wildcards': wildcards_to_delete,
        'deleted_children': children_to_delete
    }), 200


@app.route('/api/wildcards', methods=['GET'])
def api_get_wildcards():
    """獲取 Wildcard 列表（支援分頁和篩選）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    is_active = request.args.get('is_active', type=str)
    untranslated_first = request.args.get('untranslated_first', 'false').lower() == 'true'

    query = Wildcard.query

    # 篩選
    if category_id:
        query = query.filter_by(category_id=category_id)

    if search:
        query = query.filter(Wildcard.content.ilike(f'%{search}%'))

    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')

    # 排序
    if untranslated_first:
        # 未翻譯的優先（content_zh 為 NULL 或空字串）
        query = query.order_by(
            db.case(
                (Wildcard.content_zh == None, 0),
                (Wildcard.content_zh == '', 0),
                else_=1
            ),
            Wildcard.content
        )
    else:
        query = query.order_by(Wildcard.content)

    # 分頁
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [w.to_dict() for w in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@app.route('/api/wildcards', methods=['POST'])
def api_create_wildcard():
    """建立新 Wildcard"""
    data = request.json
    if not data or 'content' not in data or 'category_id' not in data:
        return jsonify({'error': '缺少必要欄位: content 和 category_id'}), 400

    wildcard = Wildcard(
        content=data['content'],
        category_id=data['category_id'],
        content_zh=data.get('content_zh'),
        priority=data.get('priority', 0),
        is_active=data.get('is_active', True),
        tags=data.get('tags'),
        notes=data.get('notes')
    )
    db.session.add(wildcard)
    db.session.commit()
    return jsonify(wildcard.to_dict()), 201


@app.route('/api/wildcards/<int:wildcard_id>', methods=['GET'])
def api_get_wildcard(wildcard_id):
    """獲取單一 Wildcard"""
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    return jsonify(wildcard.to_dict())


def get_comfy_filepath_for_category(category, base_path):
    """
    根據分類計算在 ComfyUI 中的檔案路徑（扁平結構）

    新方式：所有檔案在同一層目錄
    檔案名格式：完整路徑用 - 連接
    例如：people/artists/anime_artists -> people-artists-anime_artists.txt
    """
    path_parts = [category.name]
    temp_cat = category
    while temp_cat.parent:
        temp_cat = temp_cat.parent
        path_parts.insert(0, temp_cat.name)

    # 使用連字符連接完整路徑作為檔案名
    filename = "-".join(path_parts) + ".txt"

    # 所有檔案都在同一個目錄
    dir_path = Path(base_path)

    return dir_path, filename


def get_category_from_filename(filename):
    """
    從扁平化的檔案名反推分類

    檔案名格式：people-artists-anime_artists.txt
    返回：最深層的分類物件
    """
    if not filename.endswith('.txt'):
        return None

    # 移除 .txt 後綴
    name_without_ext = filename[:-4]

    # 拆分路徑
    path_parts = name_without_ext.split('-')

    if not path_parts:
        return None

    # 從最深層開始查找（最後一個部分是最深層分類）
    category_name = path_parts[-1]

    # 查找匹配的分類
    # 需要確保完整路徑匹配，避免同名分類的衝突
    categories = Category.query.filter_by(name=category_name).all()

    for cat in categories:
        # 獲取此分類的完整路徑
        cat_path_parts = []
        temp_cat = cat
        while temp_cat:
            cat_path_parts.insert(0, temp_cat.name)
            temp_cat = temp_cat.parent

        # 比對路徑是否完全匹配
        if cat_path_parts == path_parts:
            return cat

    return None

@app.route('/api/wildcards/<int:wildcard_id>', methods=['PUT'])
def api_update_wildcard(wildcard_id):
    """更新 Wildcard，並在啟用/停用時同步到 ComfyUI 檔案系統"""
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    data = request.json
    
    original_is_active = wildcard.is_active
    new_is_active = data.get('is_active', original_is_active)

    # 如果啟用狀態改變，且有關聯的分類，則處理檔案
    if new_is_active != original_is_active and wildcard.category:
        comfy_path_str = get_comfy_wildcard_path()
        if comfy_path_str:
            dir_path, filename = get_comfy_filepath_for_category(wildcard.category, comfy_path_str)
            filepath = dir_path / filename

            try:
                if new_is_active: # 從 False -> True (啟用)
                    print(f"[扁平化] 啟用 Wildcard:")
                    print(f"  - 基礎目錄: {dir_path}")
                    print(f"  - 檔案名: {filename}")
                    print(f"  - 完整路徑: {filepath}")
                    print(f"  - 內容: '{wildcard.content}'")
                    dir_path.mkdir(parents=True, exist_ok=True)
                    with open(filepath, 'a', encoding='utf-8') as f:
                        f.write(f"\n{wildcard.content}")
                
                else: # 從 True -> False (停用)
                    print(f"停用 Wildcard: 正在從 {filepath} 移除 '{wildcard.content}'")
                    if filepath.exists():
                        with open(filepath, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            for line in lines:
                                if line.strip() != wildcard.content:
                                    f.write(line)
            except Exception as e:
                print(f"檔案操作失敗: {e}")
                # 決定是否要因為檔案操作失敗而中斷。暫時只記錄日誌。

    # 更新資料庫中的欄位
    wildcard.content = data.get('content', wildcard.content)
    wildcard.content_zh = data.get('content_zh', wildcard.content_zh)
    wildcard.category_id = data.get('category_id', wildcard.category_id)
    wildcard.priority = data.get('priority', wildcard.priority)
    wildcard.is_active = new_is_active
    wildcard.tags = data.get('tags', wildcard.tags)
    wildcard.notes = data.get('notes', wildcard.notes)

    db.session.commit()
    return jsonify(wildcard.to_dict())


@app.route('/api/wildcards/<int:wildcard_id>', methods=['DELETE'])
def api_delete_wildcard(wildcard_id):
    """刪除 Wildcard"""
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    db.session.delete(wildcard)
    db.session.commit()
    return '', 204


@app.route('/api/wildcards/batch-delete', methods=['POST'])
def api_batch_delete_wildcards():
    """批量刪除 Wildcard"""
    data = request.json
    ids = data.get('ids', [])

    if not ids:
        return jsonify({'error': '未提供 ID'}), 400

    Wildcard.query.filter(Wildcard.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    return jsonify({'deleted': len(ids)})


@app.route('/api/wildcards/batch-update-category', methods=['POST'])
def api_batch_update_category():
    """批量更新 Wildcard 的分類"""
    data = request.json
    ids = data.get('ids', [])
    category_id = data.get('category_id')

    if not ids or not category_id:
        return jsonify({'error': '缺少必要參數: ids 和 category_id'}), 400

    # 檢查分類是否存在
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'error': '目標分類不存在'}), 404

    # TODO: 將來可以增加檔案移動的邏輯
    # 目前只更新資料庫

    updated_count = Wildcard.query.filter(Wildcard.id.in_(ids)).update(
        {'category_id': category_id}, synchronize_session=False
    )
    db.session.commit()

    return jsonify({'message': f'成功將 {updated_count} 個 wildcards 移動到分類 "{category.display_name}"', 'updated': updated_count})


@app.route('/api/wildcards/batch-update-active', methods=['POST'])
def api_batch_update_active():
    """批量更新 Wildcard 的啟用狀態，並同步到 ComfyUI 檔案系統"""
    data = request.json
    ids = data.get('ids', [])
    is_active = data.get('is_active')

    if not ids or is_active is None:
        return jsonify({'error': '缺少必要參數: ids 和 is_active'}), 400

    # 查詢所有要更新的 wildcards
    wildcards = Wildcard.query.filter(Wildcard.id.in_(ids)).all()

    if not wildcards:
        return jsonify({'error': '找不到要更新的 wildcards'}), 404

    updated_count = 0
    error_count = 0
    comfy_path_str = get_comfy_wildcard_path()

    for wildcard in wildcards:
        # 只處理狀態有變化的項目
        if wildcard.is_active == is_active:
            continue

        original_is_active = wildcard.is_active

        # 如果有設定 ComfyUI 路徑且有關聯的分類，則處理檔案同步
        if comfy_path_str and wildcard.category:
            dir_path, filename = get_comfy_filepath_for_category(wildcard.category, comfy_path_str)
            filepath = dir_path / filename

            try:
                if is_active:  # 啟用
                    print(f"[扁平化] 批次啟用 Wildcard:")
                    print(f"  - 基礎目錄: {dir_path}")
                    print(f"  - 檔案名: {filename}")
                    print(f"  - 完整路徑: {filepath}")
                    print(f"  - 內容: '{wildcard.content}'")
                    dir_path.mkdir(parents=True, exist_ok=True)
                    with open(filepath, 'a', encoding='utf-8') as f:
                        f.write(f"\n{wildcard.content}")
                else:  # 停用
                    print(f"批次停用: 正在從 {filepath} 移除 '{wildcard.content}'")
                    if filepath.exists():
                        with open(filepath, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                        with open(filepath, 'w', encoding='utf-8') as f:
                            for line in lines:
                                if line.strip() != wildcard.content:
                                    f.write(line)
            except Exception as e:
                print(f"批次更新檔案操作失敗: {e}")
                error_count += 1
                continue  # 檔案操作失敗時跳過此項目

        # 更新資料庫
        wildcard.is_active = is_active
        updated_count += 1

    db.session.commit()

    action = '啟用' if is_active else '停用'
    message = f'成功{action} {updated_count} 個 wildcards'
    if error_count > 0:
        message += f'，{error_count} 個項目檔案同步失敗'

    return jsonify({
        'message': message,
        'updated': updated_count,
        'errors': error_count
    })


def get_translation_service():
    """查詢資料庫，獲取當前啟用的翻譯服務實例和設定"""
    active_setting = TranslationSetting.query.filter_by(is_active=True).first()
    if not active_setting:
        return None, None, "沒有啟用的翻譯服務"

    provider = active_setting.provider
    if provider == 'ollama':
        helper = OllamaHelper(base_url=app.config['OLLAMA_BASE_URL'], model=active_setting.model_name)
        if not helper.check_connection():
            return None, None, "Ollama 服務未運行"
        
        # 檢查模型是否存在
        available_models = helper.list_models()
        if active_setting.model_name not in available_models:
            error_msg = f"Ollama 模型 '{active_setting.model_name}' 未在 Ollama 服務中找到. " \
                        f"可用的模型: {', '.join(available_models)}. " \
                        f"請先拉取此模型或在設定中更換."
            return None, None, error_msg
            
        return helper, active_setting, None

    elif provider == 'gemini':
        if not active_setting.api_key:
            return None, None, "Gemini API Key 未設定"
        helper = GeminiHelper(api_key=active_setting.api_key, model=active_setting.model_name)
        return helper, active_setting, None

    elif provider == 'pollinations':
        # Pollinations API 不一定需要 API key，但如果設定了就使用
        api_key = active_setting.api_key if active_setting.api_key else None
        helper = PollinationsHelper(api_key=api_key, model=active_setting.model_name or 'openai')
        if not helper.check_connection():
            return None, None, "Pollinations 服務連接失敗"
        return helper, active_setting, None

    return None, None, f"不支援的翻譯服務: {provider}"


@app.route('/api/wildcards/<int:wildcard_id>/translate', methods=['POST'])
def api_translate_wildcard(wildcard_id):
    """翻譯單個 Wildcard (使用資料庫設定) - 無論是否已翻譯都會重新翻譯"""
    service, settings, error = get_translation_service()
    if error:
        return jsonify({'error': error}), 503

    wildcard = Wildcard.query.get_or_404(wildcard_id)

    # 檢查是否為不需要翻譯的類別
    if wildcard.category and ('藝術家' in wildcard.category.get_full_path() or 'emoji' in wildcard.category.get_full_path().lower()):
        return jsonify({'error': '此類別無需翻譯'}), 400

    try:
        translation = service.translate_to_chinese(wildcard.content, settings.system_prompt)
        if translation:
            wildcard.content_zh = translation
            wildcard.translation_status = 'translated'
            db.session.commit()
            return jsonify({'id': wildcard.id, 'content_zh': translation, 'status': 'translated'})
        else:
            wildcard.translation_status = 'failed'
            db.session.commit()
            return jsonify({'error': '翻譯返回空結果'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/wildcards/batch-translate', methods=['POST'])
def api_batch_translate_wildcards():
    """批量翻譯 Wildcard (使用資料庫設定, 平行處理)"""
    service, settings, error = get_translation_service()
    if error:
        return jsonify({'error': error}), 503

    data = request.json
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': '未提供 ID'}), 400

    try:
        wildcards_to_process = Wildcard.query.filter(Wildcard.id.in_(ids)).all()
        
        texts_to_translate = []
        wildcards_to_update = []
        for w in wildcards_to_process:
            if not (w.content_zh and w.translation_status == 'translated'):
                if not (w.category and ('藝術家' in w.category.get_full_path() or 'emoji' in w.category.get_full_path().lower())):
                    texts_to_translate.append(w.content)
                    wildcards_to_update.append(w)

        if not texts_to_translate:
            return jsonify({'translated': 0, 'failed': 0, 'message': '沒有需要翻譯的項目'})

        translated_results = service.batch_translate(texts_to_translate, settings.system_prompt)
        
        translated_count = 0
        failed_count = 0
        for wildcard in wildcards_to_update:
            translation = translated_results.get(wildcard.content)
            if translation and translation != wildcard.content:
                wildcard.content_zh = translation
                wildcard.translation_status = 'translated'
                translated_count += 1
            else:
                wildcard.translation_status = 'failed'
                failed_count += 1
        
        db.session.commit()
        return jsonify({'translated': translated_count, 'failed': failed_count})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/upload', methods=['POST'])
def api_import_upload():
    """從上傳的檔案匯入 (TXT 或 ZIP)，可手動指定分類"""
    if 'file' not in request.files:
        return jsonify({'error': '沒有上傳檔案'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '沒有選擇檔案'}), 400

    # 從表單中獲取 category_id
    category_id = request.form.get('category_id', type=int)
    # 獲取其他選項
    use_ollama_translate = request.form.get('translate', 'false').lower() == 'true'
    use_comma_separated = request.form.get('comma_separated', 'false').lower() == 'true'


    filename = secure_filename(file.filename)
    
    with tempfile.TemporaryDirectory(prefix='wildcard_upload_') as temp_dir:
        temp_path = Path(temp_dir)
        saved_filepath = temp_path / filename
        file.save(saved_filepath)

        total_imported = 0
        total_skipped = 0
        errors = []

        try:
            if filename.lower().endswith('.zip'):
                extract_path = temp_path / 'extracted'
                extract_path.mkdir()
                with zipfile.ZipFile(saved_filepath, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                total_imported, total_skipped, errors = import_from_directory(
                    str(extract_path),
                    recursive=True,
                    target_category_id=category_id,
                    use_ollama_translate=use_ollama_translate,
                    use_comma_separated=use_comma_separated
                )

            elif filename.lower().endswith('.txt'):
                result = import_txt_file(
                    str(saved_filepath),
                    target_category_id=category_id,
                    use_ollama_translate=use_ollama_translate,
                    use_comma_separated=use_comma_separated
                )
                total_imported = result.get('imported', 0)
                total_skipped = result.get('skipped', 0)

            else:
                errors.append('不支援的檔案格式，請上傳 .txt 或 .zip 檔案')

            if not errors:
                history = ImportHistory(
                    filename=filename,
                    file_type=Path(filename).suffix.lower().strip('.'),
                    items_imported=total_imported,
                    items_skipped=total_skipped,
                    status='success'
                )
                db.session.add(history)
                db.session.commit()

            return jsonify({
                'imported': total_imported,
                'skipped': total_skipped,
                'errors': errors
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'處理檔案時發生錯誤: {str(e)}'}), 500


@app.route('/api/import/directory', methods=['POST'])
def api_import_directory():
    """從目錄匯入 wildcard 檔案"""
    data = request.json
    directory = data.get('directory', 'sample_file/wildcards')
    use_ollama_classify = data.get('use_ollama_classify', False)
    use_ollama_translate = data.get('use_ollama_translate', False)
    recursive = data.get('recursive', True)

    imported, skipped, errors = import_from_directory(
        directory,
        use_ollama_classify=use_ollama_classify,
        use_ollama_translate=use_ollama_translate,
        recursive=recursive
    )

    # 記錄匯入歷史
    history = ImportHistory(
        filename=directory,
        file_type='directory',
        items_imported=imported,
        items_skipped=skipped,
        status='success' if not errors else 'partial',
        error_message='; '.join(errors) if errors else None
    )
    db.session.add(history)
    db.session.commit()

    return jsonify({
        'imported': imported,
        'skipped': skipped,
        'errors': errors
    })


def import_from_directory(directory_path, use_ollama_classify=False, use_ollama_translate=False, recursive=True, target_category_id=None, use_comma_separated=False):
    """
    從目錄匯入所有 TXT 檔案

    Args:
        directory_path: 目錄路徑
        use_ollama_classify: 是否使用 Ollama 協助分類
        use_ollama_translate: 是否使用 Ollama 翻譯
        recursive: 是否遞迴搜尋子目錄
        target_category_id: 手動指定的目標分類 ID
        use_comma_separated: 是否啟用逗號分隔格式
    """
    imported = 0
    skipped = 0
    errors = []

    dir_path = Path(directory_path)
    if not dir_path.exists():
        errors.append(f'目錄不存在: {directory_path}')
        return imported, skipped, errors

    # 遞迴或非遞迴搜尋
    if recursive:
        txt_files = list(dir_path.rglob('*.txt'))
    else:
        txt_files = list(dir_path.glob('*.txt'))

    print(f"找到 {len(txt_files)} 個 TXT 檔案")

    for i, txt_file in enumerate(txt_files, 1):
        try:
            print(f"處理 [{i}/{len(txt_files)}]: {txt_file.name}")
            # 如果手動指定分類，則不使用 AI 分類
            current_use_ollama_classify = use_ollama_classify and not target_category_id
            
            result = import_txt_file(
                str(txt_file),
                use_ollama_classify=current_use_ollama_classify,
                use_ollama_translate=use_ollama_translate,
                target_category_id=target_category_id,
                use_comma_separated=use_comma_separated
            )
            imported += result['imported']
            skipped += result['skipped']
        except Exception as e:
            errors.append(f'{txt_file.name}: {str(e)}')

    return imported, skipped, errors


def import_txt_file(file_path, use_ollama_classify=False, use_ollama_translate=False, target_category_id=None, use_comma_separated=False):
    """
    匯入單一 TXT 檔案

    Args:
        file_path: 檔案路徑
        use_ollama_classify: 使用 Ollama 協助分類
        use_ollama_translate: 使用 Ollama 翻譯
        target_category_id: 手動指定的目標分類 ID
        use_comma_separated: 是否啟用逗號分隔格式（將 "item1, item2" 分割為多個項目）
    """
    from auto_categorizer import find_best_category, get_category_by_path

    filename = os.path.basename(file_path)
    imported = 0
    skipped = 0
    category = None

    if target_category_id:
        category = Category.query.get(target_category_id)
        use_ollama_classify = False # 手動指定分類時，不使用 AI 分類
    
    if not category:
        # 自動分類邏輯
        category = get_category_by_path(find_best_category(filename))

        # 如果找不到分類，使用預設的「其他」分類
        if not category:
            category = Category.query.filter_by(name='misc', parent_id=None).first()
            # 如果連 misc 都沒有，就創建一個
            if not category:
                category = Category(
                    name='misc',
                    display_name='其他',
                    description='自動產生的未分類項目',
                    color='#6c757d',
                    sort_order=99,
                    level=0
                )
                db.session.add(category)
                db.session.flush() # 立即獲取 ID

    # 準備 Ollama 助手（如果需要）
    ollama = None
    if use_ollama_classify or use_ollama_translate:
        try:
            from ollama_helper import OllamaHelper
            ollama = OllamaHelper(base_url=app.config['OLLAMA_BASE_URL'], model=app.config['OLLAMA_MODEL'])
            if not ollama.check_connection():
                print("警告: 無法連接到 Ollama，將不使用 AI 功能")
                ollama = None
        except Exception as e:
            print(f"Ollama 初始化失敗: {e}")
            ollama = None

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 第一步：收集所有要匯入的內容
    wildcards_to_import = []

    for line in lines:
        cleaned_line = clean_line(line)
        if not cleaned_line:
            continue

        # 根據 use_comma_separated 參數決定是否啟用逗號分隔格式
        if use_comma_separated and ',' in cleaned_line:
            # 逗號分隔格式：將一行拆分成多個項目
            items = [item.strip() for item in cleaned_line.split(',')]
        else:
            # 傳統格式：每行一個項目
            items = [cleaned_line]

        # 處理每個項目
        for raw_content in items:
            if not raw_content:
                continue

            # 清理項目內容：如果啟用逗號分隔格式，則將底線轉換為空格
            if use_comma_separated:
                content = raw_content.replace('_', ' ').strip()
            else:
                content = raw_content.strip()

            if not content:
                continue

            # 檢查是否已存在（全局去重）
            existing = Wildcard.query.filter_by(content=content).first()

            if existing:
                skipped += 1
                continue

            # 如果使用 Ollama 協助分類
            current_category = category
            if use_ollama_classify and ollama:
                try:
                    # 獲取所有可用分類
                    all_categories = Category.query.all()
                    categories_info = [
                        {
                            'full_path': cat.get_full_path('/'),
                            'description': cat.description or ''
                        }
                        for cat in all_categories if cat.level <= 2  # 只提供到第2層
                    ]

                    suggested_path = ollama.suggest_category(content, filename, categories_info)
                    if suggested_path:
                        suggested_cat = get_category_by_path(suggested_path.strip())
                        if suggested_cat:
                            current_category = suggested_cat
                except Exception as e:
                    print(f"AI 分類失敗: {e}")

            # 創建 wildcard 記錄（先不翻譯）
            wildcard = Wildcard(
                content=content,
                category_id=current_category.id,
                source_file=filename,
                translation_status='pending' if use_ollama_translate else 'skipped'
            )

            wildcards_to_import.append(wildcard)
            db.session.add(wildcard)
            imported += 1

    # 第二步：批次翻譯（如果啟用）
    if use_ollama_translate and ollama and wildcards_to_import:
        try:
            print(f"開始批次翻譯 {len(wildcards_to_import)} 個項目...")

            # 收集需要翻譯的文本
            texts_to_translate = [w.content for w in wildcards_to_import]

            # 批次翻譯
            translation_results = ollama.batch_translate(texts_to_translate, batch_size=10, show_progress=True)

            # 更新翻譯結果
            for wildcard in wildcards_to_import:
                if wildcard.content in translation_results:
                    translation = translation_results[wildcard.content]
                    if translation and translation != wildcard.content:  # 確保有翻譯且不是原文
                        wildcard.content_zh = translation
                        wildcard.translation_status = 'translated'
                    else:
                        wildcard.translation_status = 'failed'
                else:
                    wildcard.translation_status = 'failed'

            print(f"批次翻譯完成！")

        except Exception as e:
            print(f"批次翻譯失敗: {e}")
            # 標記所有為失敗
            for wildcard in wildcards_to_import:
                if wildcard.translation_status == 'pending':
                    wildcard.translation_status = 'failed'

        # 每100條提交一次
        if imported % 100 == 0:
            db.session.commit()

    db.session.commit()
    return {'imported': imported, 'skipped': skipped}


def categorize_filename(filename):
    """根據檔名判斷類別"""
    filename_lower = filename.lower()
    name_without_ext = os.path.splitext(filename_lower)[0]

    category_keywords = {
        'characters': ['actor', 'actress', 'character', 'person', 'celebrity'],
        'styles': ['style', 'art', 'aesthetic', 'theme'],
        'adjectives': ['adj-', 'adjective'],
        'technical': ['3d', 'render', 'engine', 'camera'],
        'scenes': ['scene', 'background', 'environment', 'location'],
        'objects': ['object', 'item', 'prop'],
        'colors': ['color', 'colour'],
    }

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in name_without_ext:
                return category

    return 'misc'


def clean_line(line):
    """清理每一行資料"""
    # 移除行號（格式如 "1→" 或 "  123→"）
    line = re.sub(r'^\s*\d+→', '', line)
    return line.strip()


@app.route('/api/export/<format>')
def api_export(format):
    """匯出資料"""
    if format not in ['txt', 'json', 'csv']:
        return jsonify({'error': '不支援的格式'}), 400

    category_id = request.args.get('category_id', type=int)
    filename = request.args.get('filename', '')  # 自定義檔名

    query = Wildcard.query.filter_by(is_active=True)
    if category_id:
        query = query.filter_by(category_id=category_id)
        category = Category.query.get(category_id)
        category_name = category.name if category else 'unknown'
    else:
        category_name = 'all'

    wildcards = query.all()

    # 決定檔名
    if not filename:
        filename = f'wildcards_{category_name}'

    if format == 'json':
        from flask import Response
        import json
        output = json.dumps([w.to_dict() for w in wildcards], ensure_ascii=False, indent=2)
        return Response(
            output,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename={filename}.json'}
        )

    elif format == 'txt':
        # TXT 格式：每行一個 wildcard
        from flask import Response
        lines = [w.content for w in wildcards]
        output = '\n'.join(lines)
        return Response(
            output,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment;filename={filename}.txt'}
        )

    elif format == 'csv':
        # CSV 格式：完整資訊
        from flask import Response
        import csv
        from io import StringIO

        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(['ID', 'Content', 'Content_ZH', 'Category', 'Source_File', 'Tags', 'Priority', 'Notes'])

        for w in wildcards:
            writer.writerow([
                w.id,
                w.content,
                w.content_zh or '',
                w.category.display_name if w.category else '',
                w.source_file or '',
                ', '.join([t.name for t in w.tags]),
                w.priority,
                w.notes or ''
            ])

        output = si.getvalue()
        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename={filename}.csv'}
        )


@app.route('/api/comfy-wildcard/scan')
def api_scan_comfy_wildcard():
    """掃描 ComfyUI Wildcard 目錄結構（扁平化檔案結構）"""
    comfy_path_str = get_comfy_wildcard_path()
    if not comfy_path_str:
        return jsonify({'error': 'COMFYUI_WILDCARD_PATH 未設定'}), 400

    comfy_path = Path(comfy_path_str)

    if not comfy_path.exists():
        return jsonify({'error': '目錄不存在'}), 404

    def build_tree_from_flat_files(files):
        """從扁平化檔案名稱建立樹狀結構"""
        root = {
            'name': 'Comfy_Wildcard',
            'path': 'Comfy_Wildcard',
            'type': 'directory',
            'children': [],
            'file_count': 0,
            'total_lines': 0
        }

        # 用於快速查找節點
        node_map = {}

        for file_info in files:
            filename = file_info['name']

            # 解析檔案名稱 (例如: people__artists__anime_artists.txt)
            if not filename.endswith('.txt'):
                continue

            name_without_ext = filename[:-4]
            path_parts = name_without_ext.split('__')

            # 建立或查找樹狀節點
            current_node = root
            current_path = []

            for i, part in enumerate(path_parts):
                current_path.append(part)
                path_key = '__'.join(current_path)

                # 檢查節點是否已存在
                if path_key not in node_map:
                    # 創建新節點
                    is_leaf = (i == len(path_parts) - 1)

                    if is_leaf:
                        # 這是檔案節點
                        new_node = {
                            'name': filename,
                            'path': '__'.join(current_path),
                            'type': 'file',
                            'size': file_info['size'],
                            'lines': file_info['lines'],
                            'modified': file_info['modified']
                        }
                        current_node['children'].append(new_node)
                        root['file_count'] += 1
                        root['total_lines'] += file_info['lines']
                    else:
                        # 這是目錄節點
                        new_node = {
                            'name': part,
                            'path': '__'.join(current_path),
                            'type': 'directory',
                            'children': [],
                            'file_count': 0,
                            'total_lines': 0
                        }
                        current_node['children'].append(new_node)
                        node_map[path_key] = new_node
                        current_node = new_node
                else:
                    # 節點已存在，繼續向下
                    current_node = node_map[path_key]

        return root

    try:
        # 掃描所有 .txt 檔案（只在基礎目錄，不遞迴）
        files = []
        for txt_file in comfy_path.glob('*.txt'):
            if txt_file.name.startswith('.'):
                continue

            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    lines = len([line for line in f if line.strip()])

                files.append({
                    'name': txt_file.name,
                    'size': txt_file.stat().st_size,
                    'lines': lines,
                    'modified': datetime.fromtimestamp(txt_file.stat().st_mtime).isoformat()
                })
            except Exception as e:
                print(f"讀取檔案失敗 {txt_file}: {e}")

        structure = build_tree_from_flat_files(files)

        return jsonify({
            'success': True,
            'data': structure,
            'summary': {
                'total_files': structure['file_count'],
                'total_lines': structure['total_lines'],
                'scan_time': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/comfy-wildcard/sync', methods=['POST'])
def api_sync_comfy_wildcard():
    """將 ComfyUI Wildcard 目錄同步到資料庫（扁平化檔案結構）"""
    comfy_path_str = get_comfy_wildcard_path()
    if not comfy_path_str:
        return jsonify({'error': 'COMFYUI_WILDCARD_PATH 未設定'}), 400

    comfy_path = Path(comfy_path_str)

    if not comfy_path.exists():
        return jsonify({'error': f'目錄不存在: {comfy_path_str}'}), 404

    data = request.json or {}
    dry_run = data.get('dry_run', False)

    imported_count = 0
    skipped_count = 0
    errors = []

    try:
        # 只掃描基礎目錄中的 .txt 檔案（不遞迴）
        txt_files = list(comfy_path.glob('*.txt'))

        for txt_file in txt_files:
            try:
                # --- 從扁平化檔案名稱解析分類 ---
                # 檔案名格式：people__artists__anime_artists.txt
                final_category = get_category_from_filename(txt_file.name)

                # 如果找不到對應的分類，嘗試創建
                if not final_category and not dry_run:
                    # 解析路徑部分
                    name_without_ext = txt_file.stem  # 移除 .txt
                    path_parts = name_without_ext.split('__')

                    if not path_parts:
                        errors.append(f"無法解析檔案名稱: {txt_file.name}")
                        continue

                    # 逐層創建或查找分類
                    current_parent_id = None
                    level = 0

                    for part in path_parts:
                        category_name = secure_filename(part)  # 清理名稱

                        # 查找同名同層級的分類
                        existing_cat = Category.query.filter_by(
                            name=category_name,
                            parent_id=current_parent_id
                        ).first()

                        if existing_cat:
                            final_category = existing_cat
                        else:
                            # 創建新分類
                            new_cat = Category(
                                name=category_name,
                                display_name=part,
                                level=level,
                                parent_id=current_parent_id
                            )
                            db.session.add(new_cat)
                            db.session.flush()  # 立即獲取 ID
                            final_category = new_cat

                        current_parent_id = final_category.id
                        level += 1

                if not final_category:
                    if dry_run:
                        # Dry run 模式下，嘗試查找或模擬創建
                        name_without_ext = txt_file.stem
                        path_parts = name_without_ext.split('__')
                        errors.append(f"預演模式: {txt_file.name} 將創建分類路徑: {' > '.join(path_parts)}")
                    else:
                        errors.append(f"無法為 {txt_file.name} 找到或創建分類")
                        continue

                # --- 讀取並匯入 Wildcards ---
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

                if not dry_run and final_category:
                    for line in lines:
                        # 檢查在同一個分類下是否已存在
                        existing = Wildcard.query.filter_by(
                            content=line,
                            category_id=final_category.id
                        ).first()

                        if not existing:
                            wildcard = Wildcard(
                                content=line,
                                category_id=final_category.id,
                                source_file=txt_file.name,
                                is_active=True
                            )
                            db.session.add(wildcard)
                            imported_count += 1
                        else:
                            skipped_count += 1
                else:  # Dry run
                    imported_count += len(lines)

            except Exception as e:
                errors.append(f"處理檔案 {txt_file.name} 時出錯: {str(e)}")

        if not dry_run:
            db.session.commit()

        return jsonify({
            'success': True,
            'imported': imported_count,
            'skipped': skipped_count,
            'errors': errors,
            'dry_run': dry_run
        })

    except Exception as e:
        db.session.rollback()
        # 提供更詳細的錯誤日誌
        app.logger.error(f"ComfyUI 同步時發生嚴重錯誤: {e}", exc_info=True)
        return jsonify({'error': f'同步過程中發生嚴重錯誤: {str(e)}'}), 500


@app.route('/api/sync/status-from-comfy', methods=['POST'])
def api_sync_status_from_comfy():
    """從 ComfyUI 目錄掃描並同步 wildcard 的啟用狀態（扁平化檔案結構）"""
    comfy_path_str = get_comfy_wildcard_path()
    if not comfy_path_str:
        return jsonify({'error': 'COMFYUI_WILDCARD_PATH 未設定'}), 400

    comfy_path = Path(comfy_path_str)
    if not comfy_path.exists() or not comfy_path.is_dir():
        return jsonify({'error': f'目錄不存在: {comfy_path_str}'}), 404

    try:
        # 1. 從檔案系統讀取所有 wildcards（只掃描基礎目錄）
        print(f"掃描目錄: {comfy_path}...")
        comfy_wildcards = set()
        files_scanned = 0

        # 只掃描基礎目錄中的 .txt 檔案（不遞迴）
        for txt_file in comfy_path.glob('*.txt'):
            if txt_file.name.startswith('.'):
                continue

            files_scanned += 1
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    content = line.strip()
                    if content and not content.startswith('#'):
                        comfy_wildcards.add(content)

        print(f"掃描完成. 找到 {files_scanned} 個檔案, {len(comfy_wildcards)} 個有效 wildcards.")

        # 2. 批次更新資料庫
        # 首先，全部停用
        print("停用所有 wildcards...")
        disabled_count = db.session.query(Wildcard).update({'is_active': False})

        # 接著，啟用存在於檔案中的
        print("啟用掃描到的 wildcards...")
        enabled_count = 0
        # 分批處理以避免記憶體問題和資料庫限制
        wildcard_list = list(comfy_wildcards)
        batch_size = 500
        for i in range(0, len(wildcard_list), batch_size):
            batch = wildcard_list[i:i + batch_size]
            updated = Wildcard.query.filter(Wildcard.content.in_(batch)).update(
                {'is_active': True}, synchronize_session=False
            )
            enabled_count += updated

        db.session.commit()

        return jsonify({
            'message': '同步成功',
            'files_scanned': files_scanned,
            'wildcards_found_in_files': len(comfy_wildcards),
            'total_wildcards_in_db': disabled_count,
            'activated_wildcards': enabled_count
        })

    except Exception as e:
        db.session.rollback()
        print(f"同步失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear-all-data', methods=['POST'])
def api_clear_all_data():
    """清除所有資料並重新初始化分類"""
    try:
        # 清除 ImportHistory
        num_import_history_deleted = db.session.query(ImportHistory).delete()
        
        # 清除 Wildcard
        num_wildcards_deleted = db.session.query(Wildcard).delete()

        # 清除 Category
        num_categories_deleted = db.session.query(Category).delete()
        
        db.session.commit()

        # 重新初始化預設分類
        init_categories()
        
        return jsonify({
            'message': '所有資料已清除並重新初始化分類',
            'deleted_wildcards': num_wildcards_deleted,
            'deleted_categories': num_categories_deleted,
            'deleted_import_history': num_import_history_deleted
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'清除資料失敗: {str(e)}'}), 500

@app.route('/api/settings/comfy-path', methods=['GET'])
def api_get_comfy_path():
    """獲取 ComfyUI Wildcard 監控路徑"""
    try:
        current_path = get_comfy_wildcard_path()
        return jsonify({'path': current_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/comfy-path', methods=['PUT'])
def api_update_comfy_path():
    """更新 ComfyUI Wildcard 監控路徑"""
    try:
        data = request.json
        new_path = data.get('path')
        if not new_path:
            return jsonify({'error': '缺少路徑參數'}), 400
        
        # 儲存到資料庫
        setting = AppSetting.query.filter_by(key='comfyui_wildcard_path').first()
        if setting:
            setting.value = new_path
        else:
            setting = AppSetting(key='comfyui_wildcard_path', value=new_path)
            db.session.add(setting)
        
        db.session.commit()
        
        # 更新 app.config 以供當前運行時使用
        app.config['COMFYUI_WILDCARD_PATH'] = new_path

        return jsonify({'message': 'ComfyUI 監控路徑已更新', 'path': new_path})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============= 翻譯設定 API =============

@app.route('/api/translation-settings', methods=['GET'])
def api_get_translation_settings():
    """獲取所有翻譯提供者的設定"""
    try:
        settings = TranslationSetting.query.order_by(TranslationSetting.provider).all()
        return jsonify([s.to_dict() for s in settings])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/translation-settings/<string:provider>', methods=['PUT'])
def api_update_translation_setting(provider):
    """更新指定提供者的設定"""
    try:
        setting = TranslationSetting.query.filter_by(provider=provider).first_or_404()
        data = request.json

        setting.model_name = data.get('model_name', setting.model_name)
        setting.temperature = float(data.get('temperature', setting.temperature))
        setting.system_prompt = data.get('system_prompt', setting.system_prompt)
        
        # 處理 Gemini 的 API Key
        if provider == 'gemini' and 'api_key' in data and data['api_key']:
            setting.api_key = data['api_key']

        db.session.commit()
        return jsonify(setting.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/translation-settings/activate', methods=['POST'])
def api_activate_translation_provider():
    """啟用指定的翻譯提供者"""
    try:
        data = request.json
        provider = data.get('provider')
        if not provider:
            return jsonify({'error': '未提供 provider'}), 400

        # 先將所有 provider 設為 inactive
        TranslationSetting.query.update({TranslationSetting.is_active: False})

        # 啟用指定的 provider
        setting = TranslationSetting.query.filter_by(provider=provider).first()
        if not setting:
            return jsonify({'error': f'找不到 provider: {provider}'}), 404
        
        setting.is_active = True
        db.session.commit()

        return jsonify({'message': f'{provider.upper()} 已被設為啟用中的翻譯服務'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/translation-settings/pollinations/models', methods=['GET'])
def api_get_pollinations_models():
    """獲取 Pollinations 可用的模型列表"""
    try:
        # 從資料庫獲取 Pollinations 設定（如果有 API key）
        pollinations_setting = TranslationSetting.query.filter_by(provider='pollinations').first()
        api_key = pollinations_setting.api_key if pollinations_setting else None

        # 創建臨時 helper 來獲取模型列表
        helper = PollinationsHelper(api_key=api_key)
        models = helper.list_models()

        # 如果無法獲取模型列表，返回預設列表
        if not models:
            models = ['openai', 'mistral', 'searchgpt']

        return jsonify(models)
    except Exception as e:
        print(f"獲取 Pollinations 模型列表失敗: {e}")
        # 即使失敗也返回預設列表
        return jsonify(['openai', 'mistral', 'searchgpt'])


@app.route('/api/translation-settings/test', methods=['POST'])
def api_test_translation_settings():
    """測試翻譯設定 (不安裝到資料庫)"""
    try:
        data = request.json
        test_text = data.get('text', 'a beautiful cat')
        provider = data.get('provider')
        settings_data = data.get('settings')

        if not all([test_text, provider, settings_data]):
            return jsonify({'error': '缺少必要參數: text, provider, settings'}), 400

        helper = None
        if provider == 'ollama':
            helper = OllamaHelper(base_url=app.config['OLLAMA_BASE_URL'], model=settings_data['model_name'])
            if not helper.check_connection():
                return jsonify({'error': 'Ollama 服務未連接'}), 503
        
        elif provider == 'gemini':
            # 測試時，優先使用傳入的 API key，如果沒有，則從資料庫中查找
            api_key = settings_data.get('api_key')
            if not api_key:
                db_setting = TranslationSetting.query.filter_by(provider='gemini').first()
                if db_setting:
                    api_key = db_setting.api_key

            if not api_key:
                 return jsonify({'error': '測試需要 Gemini API Key'}), 400

            helper = GeminiHelper(api_key=api_key, model=settings_data['model_name'])

        elif provider == 'pollinations':
            # Pollinations API key 是可選的
            api_key = settings_data.get('api_key')
            if not api_key:
                db_setting = TranslationSetting.query.filter_by(provider='pollinations').first()
                if db_setting:
                    api_key = db_setting.api_key

            helper = PollinationsHelper(api_key=api_key, model=settings_data['model_name'])
            if not helper.check_connection():
                return jsonify({'error': 'Pollinations 服務連接失敗'}), 503

        else:
            return jsonify({'error': f'不支援的 provider: {provider}'}), 400

        result = helper.translate_to_chinese(
            test_text,
            system_prompt=settings_data['system_prompt'],
            temperature=settings_data['temperature']
        )

        if result:
            return jsonify({
                'original': test_text,
                'translated': result,
                'settings': settings_data
            })
        else:
            return jsonify({'error': '翻譯返回空結果'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= Prompt Builder API =============

@app.route('/api/prompt-builder/wildcards', methods=['GET'])
def api_get_prompt_builder_wildcards():
    """獲取所有 wildcard 分類和內容，用於 Prompt Builder"""
    try:
        # 獲取所有啟用的 wildcards，按分類組織
        categories = Category.query.order_by(Category.level, Category.sort_order).all()

        result = []
        for category in categories:
            # 獲取此分類下所有啟用的 wildcards
            wildcards = Wildcard.query.filter_by(
                category_id=category.id,
                is_active=True
            ).order_by(Wildcard.content).all()

            if wildcards:  # 只包含有內容的分類
                result.append({
                    'id': category.id,
                    'name': category.name,
                    'display_name': category.display_name,
                    'full_path': category.get_full_path(),
                    'wildcard_path': category.get_wildcard_path(),
                    'color': category.color,
                    'level': category.level,
                    'parent_id': category.parent_id,
                    'wildcard_count': len(wildcards),
                    'wildcards': [
                        {
                            'id': w.id,
                            'content': w.content,
                            'content_zh': w.content_zh
                        } for w in wildcards
                    ]
                })

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prompt-builder/preview', methods=['POST'])
def api_preview_prompt():
    """預覽提示詞 - 隨機化 wildcard 語法，支援變數"""
    import random
    import re

    data = request.json
    prompt_template = data.get('prompt', '')

    if not prompt_template:
        return jsonify({'error': '提示詞不能為空'}), 400

    try:
        # 儲存變數的字典
        variables = {}

        # 處理 __category__ 語法（支持連字符分隔的路徑）
        def replace_category_wildcard(match):
            wildcard_path = match.group(1)
            # 從路徑中獲取分類（支持 character-hairstyle 格式）
            path_parts = wildcard_path.split('-')
            category_name = path_parts[-1]  # 取最後一部分作為分類名稱

            # 查找匹配的分類
            categories = Category.query.filter_by(name=category_name).all()
            category = None
            for cat in categories:
                # 驗證完整路徑是否匹配
                cat_wildcard_path = cat.get_wildcard_path()
                if cat_wildcard_path == wildcard_path:
                    category = cat
                    break

            if not category and len(path_parts) == 1:
                # 如果只有一層路徑，直接按名稱查找
                category = Category.query.filter_by(name=wildcard_path).first()
            if category:
                # 獲取此分類下的所有啟用 wildcards
                wildcards = Wildcard.query.filter_by(
                    category_id=category.id,
                    is_active=True
                ).all()
                if wildcards:
                    selected = random.choice(wildcards)
                    return selected.content
            return match.group(0)  # 如果找不到，返回原文

        # 處理變數定義 {$varname=value} 或 {$varname=__category__|option1|option2}
        def replace_variable_definition(match):
            var_name = match.group(1)
            var_value = match.group(2)

            # 先處理 value 中的 wildcard 和選項語法
            processed_value = var_value

            # 處理 __category__（支持連字符）
            processed_value = re.sub(r'__([a-zA-Z0-9_-]+)__', replace_category_wildcard, processed_value)

            # 處理 {option1|option2}
            if '|' in processed_value:
                options = processed_value.split('|')
                processed_value = random.choice(options).strip()

            # 儲存變數
            variables[var_name] = processed_value

            # 返回處理後的值（變數定義本身會被替換為值）
            return processed_value

        # 處理變數引用 $varname
        def replace_variable_reference(match):
            var_name = match.group(1)
            return variables.get(var_name, match.group(0))  # 如果變數不存在，返回原文

        # 處理 {option1|option2|option3} 語法（非變數定義）
        def replace_choice_wildcard(match):
            full_match = match.group(0)
            content = match.group(1)

            # 跳過變數定義語法
            if content.startswith('$') and '=' in content:
                return full_match

            options = content.split('|')
            return random.choice(options).strip()

        # 執行替換
        result = prompt_template
        max_iterations = 10

        # 第一步：處理變數定義 {$varname=value}
        for _ in range(max_iterations):
            old_result = result
            result = re.sub(r'\{\$([a-zA-Z0-9_]+)=([^}]+)\}', replace_variable_definition, result)
            if result == old_result:
                break

        # 第二步：處理 __category__ 語法（支持連字符）
        for _ in range(max_iterations):
            old_result = result
            result = re.sub(r'__([a-zA-Z0-9_-]+)__', replace_category_wildcard, result)
            if result == old_result:
                break

        # 第三步：處理 {option1|option2} 語法
        for _ in range(max_iterations):
            old_result = result
            result = re.sub(r'\{([^}]+)\}', replace_choice_wildcard, result)
            if result == old_result:
                break

        # 第四步：替換變數引用 $varname
        for _ in range(max_iterations):
            old_result = result
            result = re.sub(r'\$([a-zA-Z0-9_]+)', replace_variable_reference, result)
            if result == old_result:
                break

        return jsonify({
            'original': prompt_template,
            'preview': result,
            'variables': variables  # 返回使用的變數
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= 提示詞模板 API =============

@app.route('/api/prompt-templates', methods=['GET'])
def api_get_prompt_templates():
    """獲取所有提示詞模板"""
    templates = PromptTemplate.query.order_by(PromptTemplate.updated_at.desc()).all()
    return jsonify([t.to_dict() for t in templates])


@app.route('/api/prompt-templates/<int:template_id>', methods=['GET'])
def api_get_prompt_template(template_id):
    """獲取單一提示詞模板"""
    template = PromptTemplate.query.get_or_404(template_id)
    return jsonify(template.to_dict())


@app.route('/api/prompt-templates', methods=['POST'])
def api_create_prompt_template():
    """創建新的提示詞模板"""
    data = request.json
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'error': '缺少必要欄位: name 和 content'}), 400

    template = PromptTemplate(
        name=data['name'],
        content=data['content'],
        description=data.get('description', '')
    )
    db.session.add(template)
    db.session.commit()

    return jsonify(template.to_dict()), 201


@app.route('/api/prompt-templates/<int:template_id>', methods=['PUT'])
def api_update_prompt_template(template_id):
    """更新提示詞模板"""
    template = PromptTemplate.query.get_or_404(template_id)
    data = request.json

    if 'name' in data:
        template.name = data['name']
    if 'content' in data:
        template.content = data['content']
    if 'description' in data:
        template.description = data['description']

    db.session.commit()
    return jsonify(template.to_dict())


@app.route('/api/prompt-templates/<int:template_id>', methods=['DELETE'])
def api_delete_prompt_template(template_id):
    """刪除提示詞模板"""
    template = PromptTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    return jsonify({'message': '模板已刪除'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
