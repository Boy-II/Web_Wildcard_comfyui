# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
from webapp.models import db, Wildcard, Category
from webapp.services import wildcard_service, translation_service
from webapp.services.category_service import get_comfy_wildcard_path, get_comfy_filepath_for_category

wildcards_bp = Blueprint('wildcards', __name__)


@wildcards_bp.route('', methods=['GET'])
def api_get_wildcards():
    """獲取 Wildcard 列表（支援分頁和篩選）"""
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
            db.case(
                (Wildcard.content_zh == None, 0),
                (Wildcard.content_zh == '', 0),
                else_=1
            ),
            Wildcard.content
        )
    else:
        query = query.order_by(Wildcard.content)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [w.to_dict() for w in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@wildcards_bp.route('', methods=['POST'])
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


@wildcards_bp.route('/<int:wildcard_id>', methods=['GET'])
def api_get_wildcard(wildcard_id):
    """獲取單一 Wildcard"""
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    return jsonify(wildcard.to_dict())


@wildcards_bp.route('/<int:wildcard_id>', methods=['PUT'])
def api_update_wildcard(wildcard_id):
    """更新 Wildcard，並在啟用/停用時同步到 ComfyUI 檔案系統"""
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    data = request.json

    original_is_active = wildcard.is_active
    new_is_active = data.get('is_active', original_is_active)

    if new_is_active != original_is_active and wildcard.category:
        comfy_path_str = get_comfy_wildcard_path()
        if comfy_path_str:
            dir_path, filename = get_comfy_filepath_for_category(wildcard.category, comfy_path_str)
            filepath = dir_path / filename

            try:
                if new_is_active:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    with open(filepath, 'a', encoding='utf-8') as f:
                        f.write(f"\n{wildcard.content}")
                else:
                    if filepath.exists():
                        with open(filepath, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        with open(filepath, 'w', encoding='utf-8') as f:
                            for line in lines:
                                if line.strip() != wildcard.content:
                                    f.write(line)
            except Exception as e:
                print(f"檔案操作失敗: {e}")

    wildcard.content = data.get('content', wildcard.content)
    wildcard.content_zh = data.get('content_zh', wildcard.content_zh)
    wildcard.category_id = data.get('category_id', wildcard.category_id)
    wildcard.priority = data.get('priority', wildcard.priority)
    wildcard.is_active = new_is_active
    wildcard.tags = data.get('tags', wildcard.tags)
    wildcard.notes = data.get('notes', wildcard.notes)

    db.session.commit()
    return jsonify(wildcard.to_dict())


@wildcards_bp.route('/<int:wildcard_id>', methods=['DELETE'])
def api_delete_wildcard(wildcard_id):
    """刪除 Wildcard"""
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    db.session.delete(wildcard)
    db.session.commit()
    return '', 204


@wildcards_bp.route('/batch-delete', methods=['POST'])
def api_batch_delete_wildcards():
    """批量刪除 Wildcard"""
    data = request.json
    ids = data.get('ids', [])

    if not ids:
        return jsonify({'error': '未提供 ID'}), 400

    Wildcard.query.filter(Wildcard.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    return jsonify({'deleted': len(ids)})


@wildcards_bp.route('/batch-update-category', methods=['POST'])
def api_batch_update_category():
    """批量更新 Wildcard 的分類"""
    data = request.json
    ids = data.get('ids', [])
    category_id = data.get('category_id')

    if not ids or not category_id:
        return jsonify({'error': '缺少必要參數: ids 和 category_id'}), 400

    category = Category.query.get(category_id)
    if not category:
        return jsonify({'error': '目標分類不存在'}), 404

    updated_count = Wildcard.query.filter(Wildcard.id.in_(ids)).update(
        {'category_id': category_id}, synchronize_session=False
    )
    db.session.commit()

    return jsonify({
        'message': f'成功將 {updated_count} 個 wildcards 移動到分類 "{category.display_name}"',
        'updated': updated_count
    })


@wildcards_bp.route('/batch-update-active', methods=['POST'])
def api_batch_update_active():
    """批量更新 Wildcard 的啟用狀態，並同步到 ComfyUI 檔案系統"""
    data = request.json
    ids = data.get('ids', [])
    is_active = data.get('is_active')

    if not ids or is_active is None:
        return jsonify({'error': '缺少必要參數: ids 和 is_active'}), 400

    wildcards = Wildcard.query.filter(Wildcard.id.in_(ids)).all()

    if not wildcards:
        return jsonify({'error': '找不到要更新的 wildcards'}), 404

    updated_count = 0
    error_count = 0
    comfy_path_str = get_comfy_wildcard_path()

    for wildcard in wildcards:
        if wildcard.is_active == is_active:
            continue

        if comfy_path_str and wildcard.category:
            dir_path, filename = get_comfy_filepath_for_category(wildcard.category, comfy_path_str)
            filepath = dir_path / filename

            try:
                if is_active:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    with open(filepath, 'a', encoding='utf-8') as f:
                        f.write(f"\n{wildcard.content}")
                else:
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
                continue

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


@wildcards_bp.route('/<int:wildcard_id>/translate', methods=['POST'])
def api_translate_wildcard(wildcard_id):
    """翻譯單個 Wildcard (使用資料庫設定)"""
    wildcard = Wildcard.query.get_or_404(wildcard_id)

    if wildcard.category and ('藝術家' in wildcard.category.get_full_path() or 'emoji' in wildcard.category.get_full_path().lower()):
        return jsonify({'error': '此類別無需翻譯'}), 400

    try:
        translation = translation_service.translate(wildcard.content)
        if translation:
            wildcard.content_zh = translation
            wildcard.translation_status = 'translated'
            db.session.commit()
            return jsonify({'id': wildcard.id, 'content_zh': translation, 'status': 'translated'})
        else:
            wildcard.translation_status = 'failed'
            db.session.commit()
            return jsonify({'error': '翻譯返回空結果'}), 500
    except ValueError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@wildcards_bp.route('/batch-translate', methods=['POST'])
def api_batch_translate_wildcards():
    """批量翻譯 Wildcard (使用資料庫設定)"""
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

        translated_results = translation_service.batch_translate(texts_to_translate)

        # batch_translate returns a list aligned with texts_to_translate
        translated_count = 0
        failed_count = 0
        for i, wildcard in enumerate(wildcards_to_update):
            translation = translated_results[i] if i < len(translated_results) else None
            if translation and translation != wildcard.content:
                wildcard.content_zh = translation
                wildcard.translation_status = 'translated'
                translated_count += 1
            else:
                wildcard.translation_status = 'failed'
                failed_count += 1

        db.session.commit()
        return jsonify({'translated': translated_count, 'failed': failed_count})

    except ValueError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
