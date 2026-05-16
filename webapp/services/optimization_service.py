# -*- coding: utf-8 -*-
"""Danbooru tag optimization service.

Uses the active translation provider (same LLM / API key) but with a
specialized system prompt.  Returns {"tag": str, "zh": str} or None.
"""
import json
import re
import concurrent.futures
from typing import Optional

DEFAULT_OPTIMIZATION_PROMPT = """你是 Danbooru 標籤專家。請將輸入的圖像描述或標籤依照 Danbooru 規範進行優化，並提供繁體中文說明。

規則：
1. 使用小寫英文，空格改為底線（如 blue_eyes, long_hair, 1girl）
2. 使用最標準、最常見的 Danbooru 官方標籤詞彙
3. 移除多餘修飾語，保留核心概念
4. 若原本是多個標籤的組合描述，可拆分為多個 Danbooru 標籤，以逗號分隔
5. 人物/系列標籤格式：character_(series) 或 artist_name

只輸出純 JSON，格式如下，不要有任何其他文字：
{"tag": "optimized_english_tag", "zh": "繁體中文說明"}"""


def _get_system_prompt() -> str:
    try:
        from webapp.models import AppSetting
        row = AppSetting.query.filter_by(key='optimization_system_prompt').first()
        if row and row.value.strip():
            return row.value
    except Exception:
        pass
    return DEFAULT_OPTIMIZATION_PROMPT


def _parse_response(text: str) -> Optional[dict]:
    """Extract {tag, zh} dict from LLM response, handling markdown code blocks."""
    if not text:
        return None
    # Strip markdown code fences
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and 'tag' in data and 'zh' in data:
            return {'tag': data['tag'].strip(), 'zh': data['zh'].strip()}
    except json.JSONDecodeError:
        # Try to find JSON object inside the text
        m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if 'tag' in data and 'zh' in data:
                    return {'tag': data['tag'].strip(), 'zh': data['zh'].strip()}
            except json.JSONDecodeError:
                pass
    return None


def _build_helper():
    from webapp.models import TranslationSetting
    from flask import current_app
    setting = TranslationSetting.query.filter_by(is_active=True).first()
    if not setting:
        raise ValueError('沒有啟用的翻譯服務，請先在翻譯設定中啟用一個設定檔')
    provider = setting.provider
    if provider == 'openai':
        from webapp.helpers.openai_helper import OpenAIHelper
        return OpenAIHelper(
            base_url=setting.base_url or 'https://api.openai.com/v1',
            api_key=setting.api_key or '',
            model=setting.model_name,
        )
    elif provider == 'gemini':
        from webapp.helpers.gemini_helper import GeminiHelper
        return GeminiHelper(api_key=setting.api_key, model=setting.model_name)
    elif provider == 'ollama':
        from webapp.helpers.ollama_helper import OllamaHelper
        return OllamaHelper(
            base_url=current_app.config['OLLAMA_BASE_URL'],
            model=setting.model_name,
        )
    raise ValueError(f'不支援的 provider: {provider}')


def optimize(text: str) -> Optional[dict]:
    """Optimize a single tag. Returns {tag, zh} or None."""
    helper = _build_helper()
    raw = helper.translate_to_chinese(text, system_prompt=_get_system_prompt(), temperature=0.2)
    return _parse_response(raw)


def batch_optimize(texts: list[str], max_workers: int = 8) -> list[Optional[dict]]:
    """Optimize multiple tags in parallel. Returns list aligned with input."""
    helper = _build_helper()
    prompt = _get_system_prompt()

    def _one(text):
        raw = helper.translate_to_chinese(text, system_prompt=prompt, temperature=0.2)
        return _parse_response(raw)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_one, t) for t in texts]
        return [f.result() for f in futures]
