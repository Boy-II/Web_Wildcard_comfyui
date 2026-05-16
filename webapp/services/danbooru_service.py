# -*- coding: utf-8 -*-
"""
Danbooru tag service.
Downloads tag metadata from Danbooru API and stores in local DB for fast lookups.
"""
import time
import threading
import requests
from datetime import datetime

DANBOORU_BASE = 'https://danbooru.donmai.us'
CATEGORY_NAMES = {0: 'general', 1: 'artist', 3: 'copyright', 4: 'character', 5: 'meta'}

_download_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def _get_creds():
    from webapp.models import AppSetting
    login = AppSetting.query.filter_by(key='danbooru_login').first()
    api_key = AppSetting.query.filter_by(key='danbooru_api_key').first()
    return (
        login.value if login and login.value else None,
        api_key.value if api_key and api_key.value else None,
    )


def _request(path, params=None):
    login, api_key = _get_creds()
    p = dict(params or {})
    if login:
        p['login'] = login
    if api_key:
        p['api_key'] = api_key
    r = requests.get(f'{DANBOORU_BASE}{path}', params=p, timeout=20)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Dataset download
# ---------------------------------------------------------------------------

def _set_app_setting(key, value, app):
    from webapp.models import db, AppSetting
    with app.app_context():
        row = AppSetting.query.filter_by(key=key).first()
        if row:
            row.value = str(value)
        else:
            db.session.add(AppSetting(key=key, value=str(value)))
        db.session.commit()


def get_dataset_status():
    """Return current sync status dict (reads AppSetting directly)."""
    from webapp.models import AppSetting, DanbooruTag
    def _val(k):
        row = AppSetting.query.filter_by(key=k).first()
        return row.value if row else None

    status = _val('danbooru_sync_status') or 'idle'
    started_at = _val('danbooru_sync_started_at')

    local_count = DanbooruTag.query.count()
    last_synced = None
    if local_count:
        latest = DanbooruTag.query.order_by(DanbooruTag.synced_at.desc()).first()
        if latest:
            last_synced = latest.synced_at.isoformat()

    chk = _val('danbooru_full_checkpoint') or ''

    # Progress detail
    pages_done   = int(_val('danbooru_sync_pages') or 0)
    new_inserted = int(_val('danbooru_sync_new') or 0)
    skipped      = int(_val('danbooru_sync_skipped') or 0)
    last_tag     = _val('danbooru_sync_last_tag') or ''

    # Elapsed time
    elapsed_sec = None
    if started_at:
        try:
            from datetime import timezone
            start_dt = datetime.fromisoformat(started_at)
            elapsed_sec = int((datetime.utcnow() - start_dt).total_seconds())
        except Exception:
            pass

    return {
        'status': status,
        'started_at': started_at,
        'elapsed_sec': elapsed_sec,
        'local_count': local_count,
        'last_synced': last_synced,
        'full_checkpoint': chk,
        'pages_done': pages_done,
        'new_inserted': new_inserted,
        'skipped': skipped,
        'last_tag': last_tag,
    }


def start_download(app, force=False):
    """Kick off background download thread. Returns False if already running."""
    if not _download_lock.acquire(blocking=False):
        return False
    t = threading.Thread(target=_download_worker, args=(app, force), daemon=True)
    t.start()
    return True


def _download_worker(app, force=False):
    from webapp.models import db, AppSetting, DanbooruTag

    def _set(key, val):
        with app.app_context():
            row = AppSetting.query.filter_by(key=key).first()
            if row:
                row.value = str(val)
            else:
                db.session.add(AppSetting(key=key, value=str(val)))
            db.session.commit()

    def _req(path, params=None):
        p = dict(params or {})
        if login:
            p['login'] = login
        if api_key:
            p['api_key'] = api_key
        r = requests.get(f'{DANBOORU_BASE}{path}', params=p, timeout=20)
        r.raise_for_status()
        return r.json()

    try:
        with app.app_context():
            login, api_key = _get_creds()
            local_count = DanbooruTag.query.count()
            # Find the latest synced_at for incremental mode
            latest = DanbooruTag.query.order_by(DanbooruTag.synced_at.desc()).first()
            last_synced_dt = latest.synced_at if (latest and not force) else None

        # Determine mode
        incremental = (local_count > 0 and not force and last_synced_dt is not None)
        mode = 'incremental' if incremental else 'full'

        _set('danbooru_sync_status', f'running:{mode}')
        _set('danbooru_sync_started_at', datetime.utcnow().isoformat())
        _set('danbooru_sync_pages', '0')
        _set('danbooru_sync_new', '0')
        _set('danbooru_sync_skipped', '0')
        _set('danbooru_sync_last_tag', '')

        pages_done = 0
        new_inserted = 0
        skipped = 0

        def _flush_stats(last_tag=''):
            _set('danbooru_sync_pages', pages_done)
            _set('danbooru_sync_new', new_inserted)
            _set('danbooru_sync_skipped', skipped)
            if last_tag:
                _set('danbooru_sync_last_tag', last_tag)

        if incremental:
            # ── Incremental: only fetch tags updated since last sync ──────────
            from datetime import timedelta
            since = (last_synced_dt - timedelta(days=1)).strftime('%Y-%m-%d')
            base_params = {
                'search[order]': 'updated_at',
                'search[updated_at][gteq]': since,
                'limit': 1000,
            }
            page = 1
            while True:
                try:
                    data = _req('/tags.json', {**base_params, 'page': page})
                except Exception as e:
                    _set('danbooru_sync_status', f'error: {e}')
                    return
                if not data:
                    break
                with app.app_context():
                    now = datetime.utcnow()
                    for tag in data:
                        existing = DanbooruTag.query.filter_by(name=tag['name']).first()
                        if existing:
                            existing.post_count = tag.get('post_count', 0)
                            existing.category = tag.get('category', 0)
                            existing.is_deprecated = tag.get('is_deprecated', False)
                            existing.synced_at = now
                            skipped += 1
                        else:
                            db.session.add(DanbooruTag(
                                name=tag['name'],
                                post_count=tag.get('post_count', 0),
                                category=tag.get('category', 0),
                                is_deprecated=tag.get('is_deprecated', False),
                                synced_at=now,
                            ))
                            new_inserted += 1
                    db.session.commit()
                pages_done += 1
                _flush_stats(data[-1]['name'])
                page += 1
                time.sleep(0.05)

        else:
            # ── Full download: cursor pagination (page=a<id>), full UPSERT ───
            # Numeric pages hit Danbooru's 1000-page / 410 limit.
            # Cursor pagination has no such limit.
            last_id = 0
            while True:
                page_cursor = f'a{last_id}' if last_id else 1
                try:
                    data = _req('/tags.json', {'search[order]': 'id', 'limit': 1000, 'page': page_cursor})
                except Exception as e:
                    _set('danbooru_sync_status', f'error: {e}')
                    return
                if not data:
                    break

                with app.app_context():
                    now = datetime.utcnow()
                    for tag in data:
                        existing = DanbooruTag.query.filter_by(name=tag['name']).first()
                        if existing:
                            existing.post_count = tag.get('post_count', 0)
                            existing.category = tag.get('category', 0)
                            existing.is_deprecated = tag.get('is_deprecated', False)
                            existing.synced_at = now
                            skipped += 1
                        else:
                            db.session.add(DanbooruTag(
                                name=tag['name'],
                                post_count=tag.get('post_count', 0),
                                category=tag.get('category', 0),
                                is_deprecated=tag.get('is_deprecated', False),
                                synced_at=now,
                            ))
                            new_inserted += 1
                    db.session.commit()
                    last_id = max(t['id'] for t in data)

                pages_done += 1
                _flush_stats(data[-1]['name'])
                time.sleep(0.05)

        _set('danbooru_sync_status', 'done')
        _flush_stats()

    except Exception as e:
        _set('danbooru_sync_status', f'error: {e}')
    finally:
        _download_lock.release()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_wildcards(wildcard_ids, app_context=None):
    """
    Look up each wildcard's content in DanbooruTag table.
    Updates danbooru_status and danbooru_post_count on each Wildcard.
    Returns summary dict.
    """
    from webapp.models import db, Wildcard, DanbooruTag

    wildcards = Wildcard.query.filter(Wildcard.id.in_(wildcard_ids)).all()
    if not wildcards:
        return {'valid': 0, 'deprecated': 0, 'not_found': 0}

    # Build lookup keys: exact, space→underscore, underscore→space (all lowercased)
    def _variants(content):
        c = content.strip()
        return {c, c.lower(), c.replace(' ', '_'), c.lower().replace(' ', '_'),
                c.replace('_', ' '), c.lower().replace('_', ' ')}

    all_keys = set()
    for w in wildcards:
        all_keys.update(_variants(w.content))

    tag_map = {}
    chunk = 500
    key_list = list(all_keys)
    for i in range(0, len(key_list), chunk):
        batch = key_list[i:i + chunk]
        tags = DanbooruTag.query.filter(DanbooruTag.name.in_(batch)).all()
        for t in tags:
            tag_map[t.name] = t

    def _find_tag(content):
        for key in _variants(content):
            if key in tag_map:
                return tag_map[key]
        return None

    summary = {'valid': 0, 'deprecated': 0, 'not_found': 0}
    for w in wildcards:
        tag = _find_tag(w.content)
        if tag is None:
            w.danbooru_status = 'not_found'
            w.danbooru_post_count = None
            summary['not_found'] += 1
        elif tag.is_deprecated:
            w.danbooru_status = 'deprecated'
            w.danbooru_post_count = tag.post_count
            summary['deprecated'] += 1
        else:
            w.danbooru_status = 'valid'
            w.danbooru_post_count = tag.post_count
            summary['valid'] += 1

    db.session.commit()
    return summary


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

def suggest_completion(pattern, category_id=None, limit=300):
    """
    Find Danbooru tags matching *pattern* that are not already in local DB.
    category_id: if set, exclude tags already in that category.
    Returns list of DanbooruTag dicts sorted by post_count desc.
    """
    from webapp.models import DanbooruTag, Wildcard

    # Tags already locally available (for diff)
    existing_query = Wildcard.query
    if category_id:
        existing_query = existing_query.filter_by(category_id=category_id)
    existing_names = {w.content for w in existing_query.all()}

    q = (
        DanbooruTag.query
        .filter(
            DanbooruTag.name.like(f'%{pattern}%'),
            DanbooruTag.is_deprecated == False,
            DanbooruTag.post_count > 0,
        )
        .order_by(DanbooruTag.post_count.desc())
        .limit(limit * 2)  # fetch extra to allow filtering
    )
    results = []
    for tag in q.all():
        if tag.name not in existing_names:
            results.append(tag.to_dict())
        if len(results) >= limit:
            break
    return results
