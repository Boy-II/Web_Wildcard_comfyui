# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from webapp.models import db, Wildcard, Category
from webapp.services import translation_service

wildcards_bp = Blueprint('wildcards', __name__)


@wildcards_bp.route('', methods=['GET'])
def api_get_wildcards():
    """獲取 Wildcard 列表（支援分頁和篩選）"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 500)
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    is_active = request.args.get('is_active', type=str)
    untranslated_first = request.args.get('untranslated_first', 'false').lower() == 'true'

    query = Wildcard.query.options(joinedload(Wildcard.category))

    if category_id:
        query = query.filter_by(category_id=category_id)

    if search:
        query = query.filter(
            db.or_(
                Wildcard.content.ilike(f'%{search}%'),
                Wildcard.content_zh.ilike(f'%{search}%')
            )
        )

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
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': f"「{data['content']}」已存在於該分類中"}), 409
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

    new_is_active = data.get('is_active', wildcard.is_active)

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

    wildcards = Wildcard.query.filter(Wildcard.id.in_(ids)).all()
    existing_contents = {w.content for w in Wildcard.query.filter_by(category_id=category_id).all()}

    updated = 0
    skipped = 0
    for w in wildcards:
        if w.content in existing_contents:
            skipped += 1
        else:
            w.category_id = category_id
            existing_contents.add(w.content)
            updated += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'遷移失敗：{e}'}), 500

    msg = f'成功移動 {updated} 個至「{category.display_name}」'
    if skipped:
        msg += f'，{skipped} 個因重複略過'
    return jsonify({'message': msg, 'updated': updated, 'skipped': skipped})


@wildcards_bp.route('/batch-update-active', methods=['POST'])
def api_batch_update_active():
    """批量更新 Wildcard 的啟用狀態"""
    data = request.json
    ids = data.get('ids', [])
    is_active = data.get('is_active')

    if not ids or is_active is None:
        return jsonify({'error': '缺少必要參數: ids 和 is_active'}), 400

    updated_count = Wildcard.query.filter(Wildcard.id.in_(ids)).update(
        {'is_active': is_active}, synchronize_session=False
    )
    db.session.commit()

    action = '啟用' if is_active else '停用'
    return jsonify({
        'message': f'成功{action} {updated_count} 個 wildcards',
        'updated': updated_count,
        'errors': 0
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


@wildcards_bp.route('/<int:wildcard_id>/optimize', methods=['POST'])
def api_optimize_wildcard(wildcard_id):
    """優化單個 Wildcard tag (Danbooru 規範 + 中文說明)"""
    wildcard = Wildcard.query.get_or_404(wildcard_id)
    try:
        from webapp.services import optimization_service
        result = optimization_service.optimize(wildcard.content)
        if result:
            wildcard.content = result['tag']
            wildcard.content_zh = result['zh']
            wildcard.translation_status = 'translated'
            db.session.commit()
            return jsonify({'id': wildcard.id, 'content': result['tag'], 'content_zh': result['zh']})
        else:
            return jsonify({'error': '優化返回空結果'}), 500
    except ValueError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@wildcards_bp.route('/batch-optimize', methods=['POST'])
def api_batch_optimize_wildcards():
    """批量優化 Wildcard tags"""
    data = request.json
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': '未提供 ID'}), 400

    try:
        from webapp.services import optimization_service
        wildcards_to_process = Wildcard.query.filter(Wildcard.id.in_(ids)).all()
        texts = [w.content for w in wildcards_to_process]
        results = optimization_service.batch_optimize(texts)

        optimized_count = 0
        failed_count = 0
        for wildcard, result in zip(wildcards_to_process, results):
            if result:
                wildcard.content = result['tag']
                wildcard.content_zh = result['zh']
                wildcard.translation_status = 'translated'
                optimized_count += 1
            else:
                failed_count += 1

        db.session.commit()
        return jsonify({'optimized': optimized_count, 'failed': failed_count})

    except ValueError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@wildcards_bp.route('/duplicates', methods=['GET'])
def api_get_duplicates():
    """找出大小寫不同但重複的 wildcard 群組"""
    key_col = func.lower(Wildcard.content).label('lower_key')
    dup_keys = (
        db.session.query(func.lower(Wildcard.content))
        .group_by(func.lower(Wildcard.content))
        .having(func.count(Wildcard.id) > 1)
        .all()
    )
    dup_keys = [row[0] for row in dup_keys]

    groups = []
    for key in dup_keys:
        wildcards = (
            Wildcard.query
            .filter(func.lower(Wildcard.content) == key)
            .order_by(Wildcard.content)
            .all()
        )
        groups.append({
            'key': key,
            'items': [
                {
                    'id': w.id,
                    'content': w.content,
                    'content_zh': w.content_zh or '',
                    'category_id': w.category_id,
                    'category_name': w.category.display_name if w.category else '',
                    'is_active': w.is_active,
                }
                for w in wildcards
            ]
        })

    return jsonify({'total_groups': len(groups), 'groups': groups})


@wildcards_bp.route('/deduplicate', methods=['POST'])
def api_deduplicate():
    """自動去重：每組保留小寫版本（或第一筆），刪除其餘"""
    data = request.json or {}
    keep_ids = data.get('keep_ids', [])   # 手動指定每組要保留的 ID
    delete_ids = data.get('delete_ids', [])  # 手動指定要刪除的 ID

    if not keep_ids and not delete_ids:
        # 自動模式：找出所有重複群組，每組保留 content 最接近純小寫的那筆
        dup_keys = (
            db.session.query(func.lower(Wildcard.content))
            .group_by(func.lower(Wildcard.content))
            .having(func.count(Wildcard.id) > 1)
            .all()
        )
        to_delete = []
        for (key,) in dup_keys:
            wildcards = (
                Wildcard.query
                .filter(func.lower(Wildcard.content) == key)
                .order_by(Wildcard.content)
                .all()
            )
            # prefer exact lowercase match, else first entry
            keep = next((w for w in wildcards if w.content == key), wildcards[0])
            to_delete.extend(w.id for w in wildcards if w.id != keep.id)

        if to_delete:
            Wildcard.query.filter(Wildcard.id.in_(to_delete)).delete(synchronize_session=False)
            db.session.commit()
        return jsonify({'deleted': len(to_delete)})

    # 手動模式：直接刪除指定 IDs
    if delete_ids:
        Wildcard.query.filter(Wildcard.id.in_(delete_ids)).delete(synchronize_session=False)
        db.session.commit()
    return jsonify({'deleted': len(delete_ids)})


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
