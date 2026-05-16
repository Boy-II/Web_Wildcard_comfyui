# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, send_file, current_app, Response
from webapp.models import db, Wildcard, Category, ImportHistory
from webapp.services import translation_service
import os
import zipfile
import re
import tempfile
import uuid
import csv
import json
import yaml
from io import StringIO
from pathlib import Path
from werkzeug.utils import secure_filename

import_export_bp = Blueprint('import_export', __name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def clean_line(line):
    """清理每一行資料"""
    line = re.sub(r'^\s*\d+→', '', line)
    return line.strip()


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


def import_txt_file(file_path, use_ollama_classify=False, use_translation=False,
                    target_category_id=None, use_comma_separated=False, to_lowercase=False):
    """
    匯入單一 TXT 檔案

    Args:
        file_path: 檔案路徑
        use_ollama_classify: 使用 Ollama 協助分類
        use_translation: 使用翻譯服務翻譯
        target_category_id: 手動指定的目標分類 ID
        use_comma_separated: 是否啟用逗號分隔格式
        to_lowercase: 是否將內容全部轉為小寫
    """
    try:
        from auto_categorizer import find_best_category, get_category_by_path
    except ImportError:
        find_best_category = lambda fn: 'misc'
        get_category_by_path = lambda p: None

    filename = os.path.basename(file_path)
    imported = 0
    skipped = 0
    category = None

    if target_category_id:
        category = Category.query.get(target_category_id)
        use_ollama_classify = False

    if not category:
        category = get_category_by_path(find_best_category(filename))

        if not category:
            category = Category.query.filter_by(name='misc', parent_id=None).first()
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
                db.session.flush()

    ollama = None
    if use_ollama_classify:
        try:
            from webapp.helpers.ollama_helper import OllamaHelper
            ollama = OllamaHelper(
                base_url=current_app.config['OLLAMA_BASE_URL'],
                model=current_app.config['OLLAMA_MODEL']
            )
            if not ollama.check_connection():
                print("警告: 無法連接到 Ollama，將不使用 AI 分類功能")
                ollama = None
        except Exception as e:
            print(f"Ollama 初始化失敗: {e}")
            ollama = None

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    wildcards_to_import = []

    for line in lines:
        cleaned_line = clean_line(line)
        if not cleaned_line:
            continue

        content = cleaned_line.strip()
        if to_lowercase:
            content = content.lower()

        if not content:
            continue

        existing = Wildcard.query.filter_by(content=content).first()
        if existing:
            skipped += 1
            continue

        current_category = category
        if use_ollama_classify and ollama:
            try:
                all_categories = Category.query.all()
                categories_info = [
                    {
                        'full_path': cat.get_full_path('/'),
                        'description': cat.description or ''
                    }
                    for cat in all_categories if cat.level <= 2
                ]
                suggested_path = ollama.suggest_category(content, filename, categories_info)
                if suggested_path:
                    suggested_cat = get_category_by_path(suggested_path.strip())
                    if suggested_cat:
                        current_category = suggested_cat
            except Exception as e:
                print(f"AI 分類失敗: {e}")

        wildcard = Wildcard(
            content=content,
            category_id=current_category.id,
            source_file=filename,
            translation_status='pending' if use_translation else 'skipped'
        )
        wildcards_to_import.append(wildcard)
        db.session.add(wildcard)
        imported += 1

    if use_translation and wildcards_to_import:
        try:
            print(f"開始批次翻譯 {len(wildcards_to_import)} 個項目...")
            texts_to_translate = [w.content for w in wildcards_to_import]
            translation_results = translation_service.batch_translate(texts_to_translate)

            for i, wildcard in enumerate(wildcards_to_import):
                translation = translation_results[i] if i < len(translation_results) else None
                if translation and translation != wildcard.content:
                    wildcard.content_zh = translation
                    wildcard.translation_status = 'translated'
                else:
                    wildcard.translation_status = 'failed'

            print("批次翻譯完成！")
        except Exception as e:
            print(f"批次翻譯失敗: {e}")
            for wildcard in wildcards_to_import:
                if wildcard.translation_status == 'pending':
                    wildcard.translation_status = 'failed'

        if imported % 100 == 0:
            db.session.commit()

    db.session.commit()
    return {'imported': imported, 'skipped': skipped}


def _collect_yaml_items(node, category_map, path=None):
    """
    Recursively walk the exported YAML structure to collect (category_name, item) pairs.
    Matches the export structure: {parent: {child: [items]}} or {name: [items]}.
    path is a list of keys leading to this node.
    """
    if path is None:
        path = []

    if isinstance(node, list):
        cat_name = '_'.join(path) if path else 'misc'
        for item in node:
            if isinstance(item, str) and item.strip():
                category_map.setdefault(cat_name, []).append(item.strip())
    elif isinstance(node, dict):
        for key, value in node.items():
            _collect_yaml_items(value, category_map, path + [key])
    elif isinstance(node, str) and node.strip():
        cat_name = '_'.join(path[:-1]) if len(path) > 1 else 'misc'
        category_map.setdefault(cat_name, []).append(node.strip())


def _fix_yaml_wildcards(content: str) -> str:
    """Quote list items that use {A|B|C} ImpactWildcard syntax, which YAML misparses as dicts."""
    fixed = []
    for line in content.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith('- {') and '|' in stripped:
            indent = line[:len(line) - len(stripped)]
            value = stripped[2:].rstrip('\n')
            value = value.replace('\\', '\\\\').replace('"', '\\"')
            fixed.append(f'{indent}- "{value}"\n')
        else:
            fixed.append(line)
    return ''.join(fixed)


def import_yaml_file(file_path, target_category_id=None, to_lowercase=False):
    """
    Import a YAML file matching the export structure.
    If target_category_id is given, all items go to that category regardless of YAML keys.
    Otherwise, YAML keys are matched to category names (e.g. parent_child).
    """
    errors = []
    imported = 0
    skipped = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw = f.read()
        fixed = _fix_yaml_wildcards(raw)
        data = yaml.safe_load(fixed)
    except Exception as e:
        return {'imported': 0, 'skipped': 0, 'errors': [f'YAML 解析失敗: {e}']}

    if data is None:
        return {'imported': 0, 'skipped': 0, 'errors': ['YAML 檔案為空']}

    if target_category_id:
        target_cat = Category.query.get(target_category_id)
        if not target_cat:
            return {'imported': 0, 'skipped': 0, 'errors': [f'找不到分類 ID={target_category_id}']}

        category_map = {}
        _collect_yaml_items(data, category_map)
        all_items = [item for items in category_map.values() for item in items]

        for content in all_items:
            if to_lowercase:
                content = content.lower()
            if not content:
                continue
            if Wildcard.query.filter_by(content=content).first():
                skipped += 1
                continue
            db.session.add(Wildcard(content=content, category_id=target_cat.id))
            imported += 1
        db.session.commit()
    else:
        category_map = {}
        _collect_yaml_items(data, category_map)

        for cat_name, items in category_map.items():
            cat = Category.query.filter_by(name=cat_name).first()
            if not cat:
                errors.append(f'找不到分類「{cat_name}」，跳過 {len(items)} 個項目')
                skipped += len(items)
                continue
            for content in items:
                if to_lowercase:
                    content = content.lower()
                if not content:
                    continue
                if Wildcard.query.filter_by(content=content).first():
                    skipped += 1
                    continue
                db.session.add(Wildcard(content=content, category_id=cat.id))
                imported += 1
        db.session.commit()

    return {'imported': imported, 'skipped': skipped, 'errors': errors}


def import_from_directory(directory_path, use_ollama_classify=False, use_translation=False,
                           recursive=True, target_category_id=None, use_comma_separated=False,
                           to_lowercase=False):
    """
    從目錄匯入所有 TXT 檔案

    Args:
        directory_path: 目錄路徑
        use_ollama_classify: 是否使用 Ollama 協助分類
        use_translation: 是否使用翻譯服務翻譯
        recursive: 是否遞迴搜尋子目錄
        target_category_id: 手動指定的目標分類 ID
        use_comma_separated: 是否啟用逗號分隔格式
        to_lowercase: 是否將內容全部轉為小寫
    """
    imported = 0
    skipped = 0
    errors = []

    dir_path = Path(directory_path)
    if not dir_path.exists():
        errors.append(f'目錄不存在: {directory_path}')
        return imported, skipped, errors

    if recursive:
        txt_files = list(dir_path.rglob('*.txt'))
    else:
        txt_files = list(dir_path.glob('*.txt'))

    print(f"找到 {len(txt_files)} 個 TXT 檔案")

    for i, txt_file in enumerate(txt_files, 1):
        try:
            print(f"處理 [{i}/{len(txt_files)}]: {txt_file.name}")
            current_use_ollama_classify = use_ollama_classify and not target_category_id
            result = import_txt_file(
                str(txt_file),
                use_ollama_classify=current_use_ollama_classify,
                use_translation=use_translation,
                target_category_id=target_category_id,
                use_comma_separated=use_comma_separated,
                to_lowercase=to_lowercase
            )
            imported += result['imported']
            skipped += result['skipped']
        except Exception as e:
            errors.append(f'{txt_file.name}: {str(e)}')

    return imported, skipped, errors


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@import_export_bp.route('/import/upload', methods=['POST'])
def api_import_upload():
    """從上傳的檔案匯入 (TXT 或 ZIP)，可手動指定分類"""
    if 'file' not in request.files:
        return jsonify({'error': '沒有上傳檔案'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '沒有選擇檔案'}), 400

    category_id = request.form.get('category_id', type=int)
    use_translation = request.form.get('translate', 'false').lower() == 'true'
    use_comma_separated = request.form.get('comma_separated', 'false').lower() == 'true'
    to_lowercase = request.form.get('to_lowercase', 'false').lower() == 'true'

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
                    # Validate ZIP entries to prevent zip-slip path traversal
                    abs_extract = extract_path.resolve()
                    for member in zip_ref.namelist():
                        member_path = (abs_extract / member).resolve()
                        if not str(member_path).startswith(str(abs_extract)):
                            return jsonify({'error': f'ZIP 包含不安全的路徑: {member}'}), 400
                    zip_ref.extractall(extract_path)

                total_imported, total_skipped, errors = import_from_directory(
                    str(extract_path),
                    recursive=True,
                    target_category_id=category_id,
                    use_translation=use_translation,
                    use_comma_separated=use_comma_separated,
                    to_lowercase=to_lowercase
                )

            elif filename.lower().endswith('.txt'):
                result = import_txt_file(
                    str(saved_filepath),
                    target_category_id=category_id,
                    use_translation=use_translation,
                    use_comma_separated=use_comma_separated,
                    to_lowercase=to_lowercase
                )
                total_imported = result.get('imported', 0)
                total_skipped = result.get('skipped', 0)

            elif filename.lower().endswith(('.yaml', '.yml')):
                result = import_yaml_file(
                    str(saved_filepath),
                    target_category_id=category_id,
                    to_lowercase=to_lowercase,
                )
                total_imported = result.get('imported', 0)
                total_skipped = result.get('skipped', 0)
                errors.extend(result.get('errors', []))

            else:
                errors.append('不支援的檔案格式，請上傳 .txt、.yaml 或 .zip 檔案')

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


@import_export_bp.route('/import/directory', methods=['POST'])
def api_import_directory():
    """從目錄匯入 wildcard 檔案"""
    data = request.json
    directory = data.get('directory', 'sample_file/wildcards')
    use_ollama_classify = data.get('use_ollama_classify', False)
    use_translation = data.get('use_ollama_translate', data.get('use_translation', False))
    recursive = data.get('recursive', True)

    imported, skipped, errors = import_from_directory(
        directory,
        use_ollama_classify=use_ollama_classify,
        use_translation=use_translation,
        recursive=recursive
    )

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


@import_export_bp.route('/import/history', methods=['GET'])
def api_import_history():
    """獲取匯入歷史"""
    history = ImportHistory.query.order_by(ImportHistory.created_at.desc()).limit(50).all()
    return jsonify([h.to_dict() for h in history])


def _build_yaml_structure(wildcards):
    """
    Build nested YAML dict from wildcards grouped by category name.

    Category name convention: "parent_child" (e.g. clothing_dress)
    → YAML structure: {clothing: {dress: [items]}}
    → Wildcard syntax: __clothing/dress__

    Categories without underscore stay flat:
    → {universal: [items]}  → __universal__
    """
    nested = {}
    for w in wildcards:
        cat = w.category
        name = cat.name if cat else 'uncategorized'
        underscore = name.find('_')
        if underscore != -1:
            parent = name[:underscore]
            child  = name[underscore + 1:]
            nested.setdefault(parent, {})
            nested[parent].setdefault(child, [])
            nested[parent][child].append(w.content)
        else:
            nested.setdefault(name, [])
            if isinstance(nested[name], list):
                nested[name].append(w.content)
            else:
                # name collision: parent already has children, add as _items
                nested[name].setdefault('_items', [])
                nested[name]['_items'].append(w.content)
    return nested


@import_export_bp.route('/export/<format>')
def api_export(format):
    """匯出資料 — 支援 txt / yaml"""
    if format not in ['txt', 'yaml']:
        return jsonify({'error': '不支援的格式，請使用 txt 或 yaml'}), 400

    category_id = request.args.get('category_id', type=int)
    filename    = request.args.get('filename', '').strip()

    query = Wildcard.query.filter_by(is_active=True)
    if category_id:
        query = query.filter_by(category_id=category_id)
        cat = Category.query.get(category_id)
        category_name = cat.name if cat else 'unknown'
    else:
        category_name = 'all'

    wildcards = query.order_by(Wildcard.content).all()

    if not filename:
        filename = f'wildcards_{category_name}'

    if format == 'txt':
        output = '\n'.join(w.content for w in wildcards)
        return Response(
            output,
            mimetype='text/plain; charset=utf-8',
            headers={'Content-Disposition': f'attachment;filename={filename}.txt'}
        )

    elif format == 'yaml':
        structure = _build_yaml_structure(wildcards)
        output = yaml.dump(
            structure,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=True,
        )
        return Response(
            output,
            mimetype='text/yaml; charset=utf-8',
            headers={'Content-Disposition': f'attachment;filename={filename}.yaml'}
        )
