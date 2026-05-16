# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
from webapp.models import db, Category, Wildcard, ImportHistory, AppSetting, TranslationSetting
from webapp.services import translation_service
from sqlalchemy import func

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/stats')
def api_stats():
    """獲取統計資訊（簡化版）"""
    total_wildcards = Wildcard.query.count()
    active_wildcards = Wildcard.query.filter_by(is_active=True).count()
    total_categories = Category.query.count()

    return jsonify({
        'total_wildcards': total_wildcards,
        'active_wildcards': active_wildcards,
        'total_categories': total_categories,
    })



@settings_bp.route('/data/clear', methods=['POST'])
def api_clear_all_data():
    """清除所有資料並重新初始化分類"""
    try:
        num_import_history_deleted = db.session.query(ImportHistory).delete()
        num_wildcards_deleted = db.session.query(Wildcard).delete()
        num_categories_deleted = db.session.query(Category).delete()
        db.session.commit()

        # Re-initialize default categories
        from webapp.init_data import init_categories
        init_categories()

        return jsonify({
            'message': '所有資料已清除並重新初始化分類',
            'deleted_wildcards': num_wildcards_deleted,
            'deleted_categories': num_categories_deleted,
            'deleted_import_history': num_import_history_deleted
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'清除資料失敗: {str(e)}'}), 500


@settings_bp.route('/translation-settings', methods=['GET'])
def api_get_translation_settings():
    """獲取所有翻譯提供者的設定"""
    try:
        settings = TranslationSetting.query.order_by(TranslationSetting.provider).all()
        return jsonify([s.to_dict() for s in settings])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/translation-settings/<string:provider>', methods=['PUT'])
def api_update_translation_setting(provider):
    """更新指定提供者的設定"""
    try:
        setting = TranslationSetting.query.filter_by(provider=provider).first_or_404()
        data = request.json

        setting.model_name = data.get('model_name', setting.model_name)
        setting.temperature = float(data.get('temperature', setting.temperature))
        setting.system_prompt = data.get('system_prompt', setting.system_prompt)

        # Handle API key for providers that need it
        if 'api_key' in data and data['api_key']:
            setting.api_key = data['api_key']

        # Handle base_url (e.g. for OpenAI-compatible providers)
        if 'base_url' in data and data['base_url']:
            setting.base_url = data['base_url']

        db.session.commit()
        return jsonify(setting.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/translation-settings/activate', methods=['POST'])
def api_activate_translation_provider():
    """啟用指定的翻譯提供者"""
    try:
        data = request.json
        provider = data.get('provider')
        if not provider:
            return jsonify({'error': '未提供 provider'}), 400

        TranslationSetting.query.update({TranslationSetting.is_active: False})

        setting = TranslationSetting.query.filter_by(provider=provider).first()
        if not setting:
            return jsonify({'error': f'找不到 provider: {provider}'}), 404

        setting.is_active = True
        db.session.commit()

        return jsonify({'message': f'{provider.upper()} 已被設為啟用中的翻譯服務'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/translation-settings/test', methods=['POST'])
def api_test_translation_settings():
    """測試翻譯設定 (不安裝到資料庫)"""
    try:
        data = request.json
        test_text = data.get('text', 'a beautiful cat')
        provider = data.get('provider')
        settings_data = data.get('settings')

        if not all([test_text, provider, settings_data]):
            return jsonify({'error': '缺少必要參數: text, provider, settings'}), 400

        # Fetch the db setting for api_key fallback
        db_setting = TranslationSetting.query.filter_by(provider=provider).first()

        result = translation_service.translate_with_override(test_text, provider, settings_data, db_setting)

        if result:
            return jsonify({
                'original': test_text,
                'translated': result,
                'settings': settings_data
            })
        else:
            return jsonify({'error': '翻譯返回空結果'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/translation-settings/system-prompt', methods=['GET'])
def api_get_shared_system_prompt():
    setting = AppSetting.query.filter_by(key='translation_system_prompt').first()
    return jsonify({'system_prompt': setting.value if setting else ''})


@settings_bp.route('/translation-settings/system-prompt', methods=['PUT'])
def api_save_shared_system_prompt():
    data = request.json or {}
    prompt = data.get('system_prompt', '')
    setting = AppSetting.query.filter_by(key='translation_system_prompt').first()
    if setting:
        setting.value = prompt
    else:
        setting = AppSetting(key='translation_system_prompt', value=prompt)
        db.session.add(setting)
    db.session.commit()
    return jsonify({'message': '共用提示詞已儲存'})


@settings_bp.route('/translation-settings/optimization-prompt', methods=['GET'])
def api_get_optimization_prompt():
    setting = AppSetting.query.filter_by(key='optimization_system_prompt').first()
    return jsonify({'system_prompt': setting.value if setting else ''})


@settings_bp.route('/translation-settings/optimization-prompt', methods=['PUT'])
def api_save_optimization_prompt():
    data = request.json or {}
    prompt = data.get('system_prompt', '')
    setting = AppSetting.query.filter_by(key='optimization_system_prompt').first()
    if setting:
        setting.value = prompt
    else:
        setting = AppSetting(key='optimization_system_prompt', value=prompt)
        db.session.add(setting)
    db.session.commit()
    return jsonify({'message': '優化提示詞已儲存'})


@settings_bp.route('/translation-settings/openai/probe-models', methods=['POST'])
def api_probe_openai_models():
    data = request.json or {}
    base_url = data.get('base_url', '').strip()
    api_key = data.get('api_key', '').strip()
    if not base_url:
        return jsonify({'error': '請提供 Base URL'}), 400
    try:
        from webapp.helpers.openai_helper import OpenAIHelper
        models = OpenAIHelper(base_url=base_url, api_key=api_key).list_models()
        if not models:
            return jsonify({'error': '無法取得模型列表'}), 400
        return jsonify(models)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/admin/migrate-flatten', methods=['POST'])
def api_migrate_flatten():
    """One-time: flatten multi-level category tree to single level."""
    try:
        from migrate_flatten_categories import run_migration
        result = run_migration()
        return jsonify({'message': '扁平化遷移完成', **result})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
