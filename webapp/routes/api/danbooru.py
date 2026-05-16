# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
import requests as http_requests
from webapp.models import db, AppSetting, Wildcard, Category, DanbooruTag
from webapp.services import danbooru_service

danbooru_bp = Blueprint('danbooru', __name__)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@danbooru_bp.route('/settings', methods=['GET'])
def api_get_settings():
    def _val(k):
        row = AppSetting.query.filter_by(key=k).first()
        return row.value if row else ''

    login = _val('danbooru_login')
    has_key = bool(_val('danbooru_api_key'))
    return jsonify({'login': login, 'has_api_key': has_key})


@danbooru_bp.route('/settings', methods=['PUT'])
def api_save_settings():
    data = request.json or {}

    def _set(k, v):
        if v is None:
            return
        row = AppSetting.query.filter_by(key=k).first()
        if row:
            row.value = v
        else:
            db.session.add(AppSetting(key=k, value=v))

    _set('danbooru_login', data.get('login', '').strip() or None)
    if data.get('api_key'):
        _set('danbooru_api_key', data['api_key'].strip())
    db.session.commit()
    return jsonify({'message': '設定已儲存'})


# ---------------------------------------------------------------------------
# Dataset download
# ---------------------------------------------------------------------------

@danbooru_bp.route('/dataset-status', methods=['GET'])
def api_dataset_status():
    return jsonify(danbooru_service.get_dataset_status())


@danbooru_bp.route('/download', methods=['POST'])
def api_start_download():
    data = request.json or {}
    force = bool(data.get('force', False))
    started = danbooru_service.start_download(current_app._get_current_object(), force=force)
    if not started:
        return jsonify({'message': '下載已在進行中'}), 409
    mode = '完整重新下載' if force else '增量更新'
    return jsonify({'message': f'開始{mode} Danbooru tag 資料庫...'})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@danbooru_bp.route('/validate', methods=['POST'])
def api_validate():
    """Validate wildcard tags against local DanbooruTag cache.
    Body: { category_id: int (optional), ids: [int] (optional) }
    If neither is provided, validate all wildcards.
    """
    data = request.json or {}
    category_id = data.get('category_id')
    ids = data.get('ids')

    if DanbooruTag.query.count() == 0:
        return jsonify({'error': '本地 tag 資料庫是空的，請先下載資料'}), 400

    if ids:
        wildcard_ids = ids
    elif category_id:
        wildcard_ids = [w.id for w in Wildcard.query.filter_by(category_id=category_id).all()]
    else:
        wildcard_ids = [w.id for w in Wildcard.query.all()]

    if not wildcard_ids:
        return jsonify({'valid': 0, 'deprecated': 0, 'not_found': 0, 'total': 0})

    summary = danbooru_service.validate_wildcards(wildcard_ids)
    summary['total'] = len(wildcard_ids)
    return jsonify(summary)


@danbooru_bp.route('/validation-results', methods=['GET'])
def api_validation_results():
    """Return wildcards with their danbooru_status for a category."""
    category_id = request.args.get('category_id', type=int)
    status_filter = request.args.get('status')  # valid / deprecated / not_found

    q = Wildcard.query.filter(Wildcard.danbooru_status != None)
    if category_id:
        q = q.filter_by(category_id=category_id)
    if status_filter:
        q = q.filter_by(danbooru_status=status_filter)

    wildcards = q.order_by(Wildcard.danbooru_status, Wildcard.content).all()
    return jsonify([{
        'id': w.id,
        'content': w.content,
        'content_zh': w.content_zh or '',
        'category_id': w.category_id,
        'category_name': w.category.display_name if w.category else '',
        'danbooru_status': w.danbooru_status,
        'danbooru_post_count': w.danbooru_post_count,
        'is_active': w.is_active,
    } for w in wildcards])


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

@danbooru_bp.route('/complete', methods=['GET'])
def api_complete():
    """Suggest missing Danbooru tags for a local category.
    Params: category_id (int), pattern (str), limit (int)
    """
    category_id = request.args.get('category_id', type=int)
    pattern = request.args.get('pattern', '').strip()
    limit = request.args.get('limit', 200, type=int)

    if not pattern:
        return jsonify({'error': '請提供搜尋關鍵字'}), 400

    if DanbooruTag.query.count() == 0:
        return jsonify({'error': '本地 tag 資料庫是空的，請先下載資料'}), 400

    results = danbooru_service.suggest_completion(pattern, category_id=category_id, limit=limit)
    return jsonify(results)


# ---------------------------------------------------------------------------
# Image browse (for prompt builder Danbooru tab)
# ---------------------------------------------------------------------------

@danbooru_bp.route('/browse', methods=['GET'])
def api_browse():
    """Proxy Danbooru post search for the prompt builder.
    Params: tags (str), limit (int, default 20), page (int, default 1)
    Returns: { posts: [...], total: int }
    """
    def _val(k):
        row = AppSetting.query.filter_by(key=k).first()
        return row.value if row else ''

    tags = request.args.get('tags', '').strip()
    limit = min(request.args.get('limit', 20, type=int), 50)
    page = max(request.args.get('page', 1, type=int), 1)

    login = _val('danbooru_login')
    api_key = _val('danbooru_api_key')

    params = {
        'tags': tags,
        'limit': limit,
        'page': page,
    }
    auth = (login, api_key) if login and api_key else None

    try:
        resp = http_requests.get(
            'https://danbooru.donmai.us/posts.json',
            params=params,
            auth=auth,
            timeout=15,
            headers={'User-Agent': 'WildcardStudio/1.0'}
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        return jsonify({'error': f'Danbooru 請求失敗: {e}'}), 502

    posts = []
    for p in raw:
        posts.append({
            'id': p.get('id'),
            'preview_url': p.get('preview_file_url') or p.get('large_file_url') or '',
            'large_url': p.get('large_file_url') or p.get('file_url') or '',
            'tags_general': (p.get('tag_string_general') or '').split(),
            'tags_character': (p.get('tag_string_character') or '').split(),
            'tags_artist': (p.get('tag_string_artist') or '').split(),
            'tags_copyright': (p.get('tag_string_copyright') or '').split(),
            'rating': p.get('rating', 'g'),
            'score': p.get('score', 0),
        })

    return jsonify({'posts': posts, 'total': len(posts), 'page': page})


@danbooru_bp.route('/import-tags', methods=['POST'])
def api_import_tags():
    """Import selected Danbooru tags into a local category."""
    data = request.json or {}
    category_id = data.get('category_id')
    tag_names = data.get('tags', [])

    if not category_id or not tag_names:
        return jsonify({'error': '缺少 category_id 或 tags'}), 400

    category = Category.query.get(category_id)
    if not category:
        return jsonify({'error': '分類不存在'}), 404

    imported = 0
    skipped = 0
    for name in tag_names:
        existing = Wildcard.query.filter_by(content=name, category_id=category_id).first()
        if existing:
            skipped += 1
            continue
        # Look up post count from local cache
        dtag = DanbooruTag.query.filter_by(name=name).first()
        w = Wildcard(
            content=name,
            category_id=category_id,
            danbooru_status='valid',
            danbooru_post_count=dtag.post_count if dtag else None,
            translation_status='pending',
        )
        db.session.add(w)
        imported += 1

    db.session.commit()
    return jsonify({
        'imported': imported,
        'skipped': skipped,
        'message': f'已匯入 {imported} 筆，跳過 {skipped} 筆重複'
    })
