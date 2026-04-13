# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
from webapp.models import db, Category, Wildcard, ImportHistory
from webapp.services.category_service import (
    get_comfy_wildcard_path, get_comfy_filepath_for_category, get_category_from_filename
)
import os
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename

comfy_bp = Blueprint('comfy', __name__)


@comfy_bp.route('/scan')
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

        node_map = {}

        for file_info in files:
            filename = file_info['name']

            if not filename.endswith('.txt'):
                continue

            name_without_ext = filename[:-4]
            path_parts = name_without_ext.split('__')

            current_node = root
            current_path = []

            for i, part in enumerate(path_parts):
                current_path.append(part)
                path_key = '__'.join(current_path)

                if path_key not in node_map:
                    is_leaf = (i == len(path_parts) - 1)

                    if is_leaf:
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
                    current_node = node_map[path_key]

        return root

    try:
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


@comfy_bp.route('/sync', methods=['POST'])
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
        txt_files = list(comfy_path.glob('*.txt'))

        for txt_file in txt_files:
            try:
                final_category = get_category_from_filename(txt_file.name)

                if not final_category and not dry_run:
                    name_without_ext = txt_file.stem
                    path_parts = name_without_ext.split('__')

                    if not path_parts:
                        errors.append(f"無法解析檔案名稱: {txt_file.name}")
                        continue

                    current_parent_id = None
                    level = 0

                    for part in path_parts:
                        category_name = secure_filename(part)

                        existing_cat = Category.query.filter_by(
                            name=category_name,
                            parent_id=current_parent_id
                        ).first()

                        if existing_cat:
                            final_category = existing_cat
                        else:
                            new_cat = Category(
                                name=category_name,
                                display_name=part,
                                level=level,
                                parent_id=current_parent_id
                            )
                            db.session.add(new_cat)
                            db.session.flush()
                            final_category = new_cat

                        current_parent_id = final_category.id
                        level += 1

                if not final_category:
                    if dry_run:
                        name_without_ext = txt_file.stem
                        path_parts = name_without_ext.split('__')
                        errors.append(f"預演模式: {txt_file.name} 將創建分類路徑: {' > '.join(path_parts)}")
                    else:
                        errors.append(f"無法為 {txt_file.name} 找到或創建分類")
                        continue

                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

                if not dry_run and final_category:
                    for line in lines:
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
                else:
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
        current_app.logger.error(f"ComfyUI 同步時發生嚴重錯誤: {e}", exc_info=True)
        return jsonify({'error': f'同步過程中發生嚴重錯誤: {str(e)}'}), 500


@comfy_bp.route('/sync/status-from-comfy', methods=['POST'])
def api_sync_status_from_comfy():
    """從 ComfyUI 目錄掃描並同步 wildcard 的啟用狀態（扁平化檔案結構）"""
    comfy_path_str = get_comfy_wildcard_path()
    if not comfy_path_str:
        return jsonify({'error': 'COMFYUI_WILDCARD_PATH 未設定'}), 400

    comfy_path = Path(comfy_path_str)
    if not comfy_path.exists() or not comfy_path.is_dir():
        return jsonify({'error': f'目錄不存在: {comfy_path_str}'}), 404

    try:
        print(f"掃描目錄: {comfy_path}...")
        comfy_wildcards = set()
        files_scanned = 0

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

        print("停用所有 wildcards...")
        disabled_count = db.session.query(Wildcard).update({'is_active': False})

        print("啟用掃描到的 wildcards...")
        enabled_count = 0
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
