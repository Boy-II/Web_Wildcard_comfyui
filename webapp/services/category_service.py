# -*- coding: utf-8 -*-
"""Category business logic."""

from webapp.models import db, Category


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
    if 'name' in data and data['name'] and data['name'] != category.name:
        new_name = data['name'].strip()
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', new_name):
            raise ValueError('系統名稱只能包含英文字母、數字和底線')
        conflict = Category.query.filter(Category.name == new_name, Category.id != category.id).first()
        if conflict:
            raise ValueError(f'系統名稱「{new_name}」已被其他分類使用')
        category.name = new_name
    category.display_name = data.get('display_name', category.display_name)
    category.description = data.get('description', category.description)
    category.color = data.get('color', category.color)
    category.sort_order = data.get('sort_order', category.sort_order)

    if 'parent_id' in data and category.parent_id != data['parent_id']:
        new_parent_id = data.get('parent_id')
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
    db.session.delete(category)
    db.session.commit()
    return {'deleted_wildcards': wildcard_count, 'deleted_children': child_count}


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
