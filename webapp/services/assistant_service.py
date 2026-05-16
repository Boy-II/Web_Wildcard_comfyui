# -*- coding: utf-8 -*-
"""
Wildcard AI Assistant service.
Uses a dedicated TranslationProfile (stored in AppSetting 'assistant_profile_id').
"""
import re

SYSTEM_PROMPT_TEMPLATE = """你是 Wildcard 管理系統的 AI 助手，協助使用者管理 Stable Diffusion / ComfyUI 的 wildcard 標籤庫。

你的能力：
• 搜尋 wildcard：根據自然語言描述找出相關 tag，並說明其用途
• 建議分類：建議某個 tag 應該歸入哪個分類
• 生成 prompt：使用 __分類/子分類__ wildcard 語法組合提示詞
• Danbooru 建議：解釋 Danbooru tag 規範、推薦標準用語
• 修改分類：更新分類的顯示名稱、描述、顏色
• 新增/刪除 wildcard：直接操作資料庫

ImpactWildcard 語法：
• __clothing/dress__   → 從 clothing_dress 分類隨機選一個

目前系統分類（ID → 系統名稱 → 顯示名稱）：
{category_list}

══ 操作指令說明 ══
若使用者要求你執行修改操作，在回覆中包含 <action> 標籤（系統會自動執行）：

更新分類（可只傳要修改的欄位）：
<action>{{"type":"update_category","id":<分類ID>,"display_name":"新名稱","description":"描述","color":"#hex"}}</action>

新增 wildcard 到分類：
<action>{{"type":"add_wildcard","category_id":<分類ID>,"content":"tag_content"}}</action>

刪除 wildcard（需要 wildcard ID）：
<action>{{"type":"delete_wildcard","id":<wildcardID>}}</action>

注意事項：
• 執行操作前，先向使用者說明將做什麼，並請求確認
• 使用者確認後才輸出 <action> 標籤
• 一次回覆可包含多個 <action> 標籤
• <action> 標籤不會顯示給使用者，只是系統執行用

當訊息中附有「[相關 wildcard]」區塊時，wildcard 資料包含 ID，可用於刪除操作。
回覆請使用繁體中文，語氣親切自然，內容具體有幫助。"""


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

def get_profile():
    """Return the TranslationProfile assigned to the assistant, or None."""
    from webapp.models import AppSetting, TranslationProfile
    row = AppSetting.query.filter_by(key='assistant_profile_id').first()
    if not row or not row.value:
        return None
    return TranslationProfile.query.get(int(row.value))


def set_profile(profile_id):
    from webapp.models import db, AppSetting
    row = AppSetting.query.filter_by(key='assistant_profile_id').first()
    if row:
        row.value = str(profile_id) if profile_id else ''
    else:
        db.session.add(AppSetting(key='assistant_profile_id', value=str(profile_id) if profile_id else ''))
    db.session.commit()


def _build_llm(profile):
    """Build the appropriate helper from a TranslationProfile."""
    from flask import current_app
    provider = profile.provider
    if provider == 'openai':
        from webapp.helpers.openai_helper import OpenAIHelper
        return OpenAIHelper(
            base_url=profile.base_url or 'https://api.openai.com/v1',
            api_key=profile.api_key or '',
            model=profile.model_name,
        )
    elif provider == 'ollama':
        from webapp.helpers.openai_helper import OpenAIHelper
        base = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/')
        return OpenAIHelper(base_url=f'{base}/v1', api_key='', model=profile.model_name)
    elif provider == 'gemini':
        from webapp.helpers.gemini_helper import GeminiHelper
        return GeminiHelper(api_key=profile.api_key, model=profile.model_name)
    raise ValueError(f'不支援的 provider: {provider}')


def _call_llm(helper, messages: list[dict], temperature: float = 0.7) -> str:
    if hasattr(helper, 'chat_messages'):
        return helper.chat_messages(messages, temperature=temperature) or '（無回應）'
    # Gemini fallback: flatten to text
    system = next((m['content'] for m in messages if m['role'] == 'system'), '')
    conv = '\n'.join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages if m['role'] != 'system'
    )
    return helper.generate(conv, system_prompt=system, temperature=temperature) or '（無回應）'


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

def _search_wildcards(query: str, limit: int = 25) -> list[dict]:
    from webapp.models import Wildcard, db
    tokens = list({t for t in re.split(r'[\s,，。、？！]+', query) if len(t) >= 2})[:6]
    if not tokens:
        return []
    conditions = [
        db.or_(Wildcard.content.ilike(f'%{t}%'), Wildcard.content_zh.ilike(f'%{t}%'))
        for t in tokens
    ]
    wildcards = (
        Wildcard.query
        .filter(db.or_(*conditions), Wildcard.is_active == True)
        .order_by(Wildcard.content)
        .limit(limit)
        .all()
    )
    return [
        {
            'id': w.id,
            'content': w.content,
            'content_zh': w.content_zh or '',
            'category': w.category.display_name if w.category else '',
            'category_name': w.category.name if w.category else '',
            'category_id': w.category_id,
        }
        for w in wildcards
    ]


def _get_categories_text() -> str:
    from webapp.models import Category
    cats = Category.query.order_by(Category.name).all()
    return '\n'.join(f'• [ID:{c.id}] {c.name} → {c.display_name}' for c in cats)


def _execute_actions(text: str) -> tuple[str, list[str]]:
    """Parse <action>JSON</action> blocks, execute them, return cleaned text + log."""
    import json
    actions_log = []

    def _run(match):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
            atype = data.get('type', '')
            if atype == 'update_category':
                from webapp.models import Category
                from webapp.services.category_service import update_category
                cat = Category.query.get(data.get('id'))
                if not cat:
                    actions_log.append(f'❌ 找不到分類 ID={data.get("id")}')
                    return ''
                update_category(cat, data)
                actions_log.append(f'✅ 已更新分類「{cat.display_name}」')
            elif atype == 'add_wildcard':
                from webapp.models import db, Wildcard, Category
                cat = Category.query.get(data.get('category_id'))
                if not cat:
                    actions_log.append(f'❌ 找不到分類 ID={data.get("category_id")}')
                    return ''
                content = (data.get('content') or '').strip()
                if not content:
                    actions_log.append('❌ wildcard 內容不能為空')
                    return ''
                if Wildcard.query.filter_by(content=content).first():
                    actions_log.append(f'⚠️ wildcard「{content}」已存在，已跳過')
                    return ''
                db.session.add(Wildcard(content=content, category_id=cat.id))
                db.session.commit()
                actions_log.append(f'✅ 已新增 wildcard「{content}」到「{cat.display_name}」')
            elif atype == 'delete_wildcard':
                from webapp.models import db, Wildcard
                w = Wildcard.query.get(data.get('id'))
                if not w:
                    actions_log.append(f'❌ 找不到 wildcard ID={data.get("id")}')
                    return ''
                name = w.content
                db.session.delete(w)
                db.session.commit()
                actions_log.append(f'✅ 已刪除 wildcard「{name}」')
            else:
                actions_log.append(f'❌ 不支援的操作類型：{atype}')
        except Exception as e:
            actions_log.append(f'❌ 操作失敗：{e}')
        return ''

    import re as _re
    clean = _re.sub(r'<action>(.*?)</action>', _run, text, flags=_re.DOTALL)
    return clean.strip(), actions_log


# ---------------------------------------------------------------------------
# Main chat entry point
# ---------------------------------------------------------------------------

def chat(message: str, history: list[dict], image: str = None) -> dict:
    """
    image: base64 data URL string, e.g. 'data:image/jpeg;base64,...'
    Passed as OpenAI vision content array when present.
    """
    profile = get_profile()
    if not profile:
        return {
            'reply': '⚠️ 尚未為 AI 助手選擇 LLM 設定檔。請點右上角「⚙」選擇一個設定檔。',
            'wildcards': [],
        }

    wildcards = _search_wildcards(message)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(category_list=_get_categories_text())

    user_text = message
    if wildcards:
        wc_lines = '\n'.join(
            f'  - [ID:{w["id"]}] {w["content"]}（{w["content_zh"]}）[分類:{w["category"]} 分類ID:{w["category_id"]}]'
            for w in wildcards
        )
        user_text = f'{message}\n\n[相關 wildcard 搜尋結果]\n{wc_lines}'

    if image:
        user_content = [
            {'type': 'text', 'text': user_text},
            {'type': 'image_url', 'image_url': {'url': image}},
        ]
    else:
        user_content = user_text

    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(history)
    messages.append({'role': 'user', 'content': user_content})

    try:
        helper = _build_llm(profile)
        raw_reply = _call_llm(helper, messages, temperature=0.7)
    except Exception as e:
        raw_reply = f'LLM 呼叫失敗：{e}'

    reply, actions_log = _execute_actions(raw_reply)
    return {'reply': reply, 'wildcards': wildcards, 'actions': actions_log}
