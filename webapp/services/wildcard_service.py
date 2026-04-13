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
        existing = filepath.read_text(encoding='utf-8') if filepath.exists() else ''
        separator = '\n' if existing and not existing.endswith('\n') else ''
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f'{separator}{wildcard.content}\n')
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
            ''.join(l for l in lines if l.strip() != wildcard.content.strip()),
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
