# -*- coding: utf-8 -*-
"""Application data initialization (seeding defaults)."""

from webapp.models import db, Category, AppSetting, TranslationSetting
from sqlalchemy.exc import OperationalError
import os

_DEFAULT_PROMPT_ZH = """你是一個專業的AI繪圖提示詞翻譯助手。你的任務是將英文的AI繪圖提示詞（wildcard）翻譯成簡潔、準確的繁體中文。

翻譯規則：
1. 只返回翻譯結果，不要加任何解釋或額外文字
2. 保持原文的核心含義
3. 對於藝術家名字，保留原文並在括號內註明中文（如果知名）
4. 對於專業術語，使用常見的中文翻譯
5. 保持簡潔，通常不超過原文長度的2倍"""


def init_all():
    init_app_settings()
    init_categories()
    init_translation_settings()


def init_app_settings():
    setting = AppSetting.query.filter_by(key='comfyui_wildcard_path').first()
    if not setting:
        default_path = os.getenv('COMFYUI_WILDCARD_PATH', '/app/comfy_wildcard')
        db.session.add(AppSetting(key='comfyui_wildcard_path', value=default_path))
        db.session.commit()
        print(f"✓ ComfyUI 路徑初始化: {default_path}")


def init_categories():
    if Category.query.count() > 0:
        return
    try:
        import importlib.util
        import os
        # Find init_categories.py relative to project root (two levels up from webapp/)
        webapp_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(webapp_dir)
        spec = importlib.util.spec_from_file_location(
            "init_categories",
            os.path.join(project_root, "init_categories.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for root_data in mod.CATEGORY_TREE:
            mod.create_category_tree(root_data)
        db.session.commit()
        print(f"✓ 已初始化 {Category.query.count()} 個分類")
    except Exception as e:
        print(f"初始化分類失敗: {e}")
        db.session.rollback()


def init_translation_settings():
    try:
        # 移除舊的 Pollinations 設定（如存在）
        pollinations = TranslationSetting.query.filter_by(provider='pollinations').first()
        if pollinations:
            db.session.delete(pollinations)
            db.session.commit()
            print("✓ 已移除 Pollinations 設定")

        if TranslationSetting.query.count() > 0:
            # 確保 openai provider 存在
            if not TranslationSetting.query.filter_by(provider='openai').first():
                db.session.add(TranslationSetting(
                    provider='openai', is_active=False,
                    base_url='https://api.openai.com/v1',
                    model_name='gpt-4o-mini', temperature=0.3,
                    system_prompt=_DEFAULT_PROMPT_ZH
                ))
                db.session.commit()
                print("✓ 已新增 OpenAI-compatible 設定")
            return

        # 全新初始化
        db.session.add(TranslationSetting(
            provider='ollama', is_active=True,
            model_name='qwen3:8b', temperature=0.3,
            system_prompt=_DEFAULT_PROMPT_ZH
        ))
        db.session.add(TranslationSetting(
            provider='gemini', is_active=False,
            model_name='models/gemini-flash-latest', temperature=0.3,
            system_prompt=_DEFAULT_PROMPT_ZH
        ))
        db.session.add(TranslationSetting(
            provider='openai', is_active=False,
            base_url='https://api.openai.com/v1',
            model_name='gpt-4o-mini', temperature=0.3,
            system_prompt=_DEFAULT_PROMPT_ZH
        ))
        db.session.commit()
        print("✓ 翻譯設定初始化完成")

    except OperationalError as e:
        print(f"資料庫 schema 錯誤: {e}")
        db.session.rollback()
    except Exception as e:
        print(f"初始化翻譯設定錯誤: {e}")
        db.session.rollback()
