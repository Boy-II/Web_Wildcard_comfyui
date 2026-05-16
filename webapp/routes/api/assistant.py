# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from webapp.models import TranslationProfile
from webapp.services import assistant_service

assistant_bp = Blueprint('assistant', __name__)


@assistant_bp.route('/settings', methods=['GET'])
def api_get_settings():
    profile = assistant_service.get_profile()
    profiles = TranslationProfile.query.order_by(TranslationProfile.name).all()
    return jsonify({
        'current_profile_id': profile.id if profile else None,
        'current_profile_name': profile.name if profile else None,
        'profiles': [{'id': p.id, 'name': p.name, 'provider': p.provider, 'model_name': p.model_name} for p in profiles],
    })


@assistant_bp.route('/settings', methods=['PUT'])
def api_save_settings():
    data = request.json or {}
    profile_id = data.get('profile_id')
    assistant_service.set_profile(profile_id)
    return jsonify({'message': '設定已儲存'})


@assistant_bp.route('/chat', methods=['POST'])
def api_chat():
    data = request.json or {}
    message = (data.get('message') or '').strip()
    history = data.get('history', [])

    if not message:
        return jsonify({'error': '訊息不能為空'}), 400

    # Validate history format
    clean_history = [
        {'role': m['role'], 'content': m['content']}
        for m in history
        if isinstance(m, dict) and m.get('role') in ('user', 'assistant') and m.get('content')
    ]

    image = (data.get('image') or '').strip() or None
    # Basic validation: must be a base64 data URL
    if image and not image.startswith('data:image/'):
        image = None

    offset = int(data.get('offset') or 0)

    try:
        result = assistant_service.chat(message, clean_history, image=image, offset=offset)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
