# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from webapp.models import db, TranslationProfile, TranslationSetting

profiles_bp = Blueprint('translation_profiles', __name__)


def _get_shared_prompt() -> str:
    from webapp.models import AppSetting
    row = AppSetting.query.filter_by(key='translation_system_prompt').first()
    return row.value if row else ''


def _sync_to_setting(profile: TranslationProfile):
    """Activate a profile by syncing its values into TranslationSetting."""
    TranslationProfile.query.filter(TranslationProfile.id != profile.id).update(
        {'is_active': False}, synchronize_session=False
    )
    profile.is_active = True

    setting = TranslationSetting.query.filter_by(provider=profile.provider).first()
    if not setting:
        setting = TranslationSetting(provider=profile.provider)
        db.session.add(setting)

    TranslationSetting.query.filter(
        TranslationSetting.provider != profile.provider
    ).update({'is_active': False}, synchronize_session=False)

    setting.is_active = True
    setting.model_name = profile.model_name
    setting.temperature = profile.temperature
    setting.system_prompt = _get_shared_prompt()   # 共用提示詞
    if profile.api_key:
        setting.api_key = profile.api_key
    if profile.base_url:
        setting.base_url = profile.base_url

    db.session.commit()


@profiles_bp.route('', methods=['GET'])
def list_profiles():
    profiles = TranslationProfile.query.order_by(
        TranslationProfile.is_active.desc(), TranslationProfile.created_at
    ).all()
    return jsonify([p.to_dict() for p in profiles])


@profiles_bp.route('', methods=['POST'])
def create_profile():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    provider = data.get('provider', 'openai')
    if not name:
        return jsonify({'error': '請提供設定檔名稱'}), 400
    if provider not in ('ollama', 'gemini', 'openai'):
        return jsonify({'error': '不支援的 provider'}), 400

    profile = TranslationProfile(
        name=name,
        provider=provider,
        model_name=data.get('model_name', ''),
        temperature=float(data.get('temperature', 0.3)),
        system_prompt=data.get('system_prompt', ''),
        api_key=data.get('api_key', ''),
        base_url=data.get('base_url', ''),
    )
    db.session.add(profile)
    db.session.commit()
    return jsonify(profile.to_dict()), 201


@profiles_bp.route('/<int:pid>', methods=['PUT'])
def update_profile(pid):
    profile = TranslationProfile.query.get_or_404(pid)
    data = request.json or {}

    if 'name' in data:
        profile.name = data['name'].strip() or profile.name
    if 'provider' in data:
        profile.provider = data['provider']
    if 'model_name' in data:
        profile.model_name = data['model_name']
    if 'temperature' in data:
        profile.temperature = float(data['temperature'])
    if 'system_prompt' in data:
        profile.system_prompt = data['system_prompt']
    if 'base_url' in data:
        profile.base_url = data['base_url']
    if data.get('api_key'):          # only update if non-empty
        profile.api_key = data['api_key']

    db.session.commit()

    # If this profile is active, re-sync to TranslationSetting
    if profile.is_active:
        _sync_to_setting(profile)

    return jsonify(profile.to_dict())


@profiles_bp.route('/<int:pid>', methods=['DELETE'])
def delete_profile(pid):
    profile = TranslationProfile.query.get_or_404(pid)
    db.session.delete(profile)
    db.session.commit()
    return jsonify({'message': '已刪除'})


@profiles_bp.route('/<int:pid>/activate', methods=['POST'])
def activate_profile(pid):
    profile = TranslationProfile.query.get_or_404(pid)
    _sync_to_setting(profile)
    return jsonify({'message': f'已啟用「{profile.name}」', 'profile': profile.to_dict()})
