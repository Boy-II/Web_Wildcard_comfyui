# -*- coding: utf-8 -*-
"""Translation dispatch — routes requests to the active provider helper."""

from webapp.models import TranslationSetting
from flask import current_app
from typing import Optional


def get_active_setting() -> TranslationSetting | None:
    return TranslationSetting.query.filter_by(is_active=True).first()


def translate(text: str) -> Optional[str]:
    """Translate using the currently active provider."""
    setting = get_active_setting()
    if not setting:
        raise ValueError('沒有啟用的翻譯服務')
    return _dispatch(text, setting.provider, setting)


def batch_translate(texts: list[str]) -> list[Optional[str]]:
    setting = get_active_setting()
    if not setting:
        raise ValueError('沒有啟用的翻譯服務')
    helper = _build_helper(setting.provider, setting)
    result = helper.batch_translate(
        texts,
        system_prompt=setting.system_prompt,
        temperature=setting.temperature,
    )
    # OllamaHelper and GeminiHelper return Dict[str, str]; OpenAIHelper returns list.
    if isinstance(result, dict):
        return [result.get(t) for t in texts]
    return result


def translate_with_override(text: str, provider: str, settings_dict: dict,
                             db_setting: TranslationSetting = None) -> Optional[str]:
    """Translate using explicit settings (for test endpoint)."""
    class _TmpSetting:
        pass
    tmp = _TmpSetting()
    tmp.provider = provider
    tmp.model_name = settings_dict.get('model_name', '')
    tmp.temperature = float(settings_dict.get('temperature', 0.3))
    tmp.system_prompt = settings_dict.get('system_prompt', '')
    tmp.api_key = settings_dict.get('api_key') or (db_setting.api_key if db_setting else '')
    tmp.base_url = settings_dict.get('base_url') or (db_setting.base_url if db_setting else '')
    return _dispatch(text, provider, tmp)


def list_models(provider: str, base_url: str = None, api_key: str = None) -> list[str]:
    if provider == 'openai':
        from webapp.helpers.openai_helper import OpenAIHelper
        setting = TranslationSetting.query.filter_by(provider='openai').first()
        _url = base_url or (setting.base_url if setting else '')
        _key = api_key or (setting.api_key if setting else '')
        return OpenAIHelper(base_url=_url, api_key=_key).list_models()
    return []


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _dispatch(text: str, provider: str, setting) -> Optional[str]:
    helper = _build_helper(provider, setting)
    return helper.translate_to_chinese(
        text,
        system_prompt=setting.system_prompt,
        temperature=setting.temperature,
    )


def _build_helper(provider: str, setting):
    if provider == 'ollama':
        from webapp.helpers.ollama_helper import OllamaHelper
        return OllamaHelper(
            base_url=current_app.config['OLLAMA_BASE_URL'],
            model=setting.model_name,
        )
    elif provider == 'gemini':
        from webapp.helpers.gemini_helper import GeminiHelper
        return GeminiHelper(api_key=setting.api_key, model=setting.model_name)
    elif provider == 'openai':
        from webapp.helpers.openai_helper import OpenAIHelper
        return OpenAIHelper(
            base_url=setting.base_url or 'https://api.openai.com/v1',
            api_key=setting.api_key or '',
            model=setting.model_name,
        )
    raise ValueError(f'不支援的 provider: {provider}')
