# -*- coding: utf-8 -*-
"""
One-time migration: flatten multi-level category tree to single level.

Before: People > Artists > Anime Artists  (name: 'anime_artists', parent_id=<artists_id>)
After:  name: 'people__artists__anime_artists', parent_id=None, level=0

Run:
  python migrate_flatten_categories.py
  # or POST /api/admin/migrate-flatten
"""

from webapp.models import db, Category


def run_migration():
    all_cats = Category.query.all()
    cat_map = {c.id: c for c in all_cats}

    def full_name(cat):
        parts = [cat.name]
        current = cat
        while current.parent_id and current.parent_id in cat_map:
            current = cat_map[current.parent_id]
            parts.insert(0, current.name)
        return '__'.join(parts)

    # Pre-compute all new names before modifying
    new_names = {c.id: full_name(c) for c in all_cats}

    # Keep if has wildcards OR is a leaf node (no children)
    keep_ids = {c.id for c in all_cats if len(c.wildcards) > 0 or len(c.children) == 0}
    delete_ids = {c.id for c in all_cats} - keep_ids

    print(f"Flattening {len(keep_ids)} categories, removing {len(delete_ids)} structural nodes...")

    # Step 1: Detach kept categories from hierarchy
    for cat_id in keep_ids:
        cat = cat_map[cat_id]
        new_name = new_names[cat_id]
        print(f"  Keep: '{cat.name}' -> '{new_name}'")
        cat.name = new_name
        cat.parent_id = None
        cat.level = 0
    db.session.flush()

    # Step 2: Delete structural nodes
    for cat_id in delete_ids:
        cat = cat_map[cat_id]
        print(f"  Remove structural: '{cat.name}'")
        db.session.execute(
            db.text('DELETE FROM categories WHERE id = :id'),
            {'id': cat_id}
        )

    db.session.commit()
    remaining = Category.query.count()
    print(f"\n✓ Migration complete. Categories remaining: {remaining}")
    return {'kept': len(keep_ids), 'removed': len(delete_ids)}


if __name__ == '__main__':
    from webapp import create_app
    with create_app().app_context():
        run_migration()
