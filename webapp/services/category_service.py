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
                    ''.join(l for l in lines if l.strip() != wildcard.content.strip()),
                    encoding='utf-8',
                )
        except Exception as e:
            print(f'[category_service] 移除 ComfyUI 檔案失敗: {e}')
    for child in cat.children:
        _remove_category_from_comfy(child, comfy_path_str)
