# -*- coding: utf-8 -*-
"""
Migration: expand wildcards.content and content_zh from VARCHAR(500) to TEXT.
Run once inside the container:  python migrate_content_to_text.py
"""
from webapp import create_app
from webapp.models import db

app = create_app()

with app.app_context():
    dialect = db.engine.dialect.name
    print(f"Database dialect: {dialect}")

    if dialect == 'postgresql':
        with db.engine.connect() as conn:
            conn.execute(db.text(
                "ALTER TABLE wildcards ALTER COLUMN content TYPE TEXT"
            ))
            conn.execute(db.text(
                "ALTER TABLE wildcards ALTER COLUMN content_zh TYPE TEXT"
            ))
            conn.commit()
        print("Migration complete: content and content_zh are now TEXT.")

    elif dialect == 'sqlite':
        # SQLite doesn't support ALTER COLUMN TYPE directly.
        # The model already uses Text, so new tables will be created correctly.
        # Existing SQLite DBs: use PRAGMA to verify current schema.
        with db.engine.connect() as conn:
            result = conn.execute(db.text("PRAGMA table_info(wildcards)"))
            for row in result:
                if row[1] in ('content', 'content_zh'):
                    print(f"  Column '{row[1]}': type={row[2]}")
        print("SQLite: no ALTER needed — model already uses Text for new DBs.")
        print("If you have an existing SQLite DB with VARCHAR(500), recreate the table manually.")

    else:
        print(f"Unsupported dialect: {dialect}. Please run the migration manually.")
