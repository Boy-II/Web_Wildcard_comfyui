# -*- coding: utf-8 -*-
import random
import re
from flask import Blueprint, render_template, request, jsonify
from webapp.models import Category, Wildcard

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
@pages_bp.route('/wildcards')
def wildcards_page():
    return render_template('wildcards.html')


@pages_bp.route('/import')
def import_page():
    return render_template('import.html')


@pages_bp.route('/export')
def export_page():
    return render_template('export.html')



@pages_bp.route('/translation-settings')
def translation_settings_page():
    return render_template('translation_settings.html')


@pages_bp.route('/prompt-builder')
def prompt_builder_page():
    return render_template('prompt_builder.html')


@pages_bp.route('/danbooru-tools')
def danbooru_tools_page():
    return render_template('danbooru_tools.html')


@pages_bp.route('/assistant')
def assistant_page():
    return render_template('assistant.html')


@pages_bp.route('/comfy-workflows')
def comfy_workflows_page():
    return render_template('comfy_workflows.html')


# ============= Prompt Builder API =============

def _impact_wildcard_path(category_name: str) -> str:
    """Convert category name to ImpactWildcard path format.

    Rule: replace the FIRST underscore with '/' so the path maps to the
    YAML nested structure exported by the system.

    Examples:
        clothing_dress     → clothing/dress
        body_breast_size   → body/breast_size
        universal          → universal  (no underscore, unchanged)
    """
    idx = category_name.find('_')
    if idx == -1:
        return category_name
    return category_name[:idx] + '/' + category_name[idx + 1:]


def _name_from_impact_path(wildcard_path: str) -> str:
    """Reverse of _impact_wildcard_path: clothing/dress → clothing_dress"""
    return wildcard_path.replace('/', '_', 1)

@pages_bp.route('/api/prompt-builder/wildcards', methods=['GET'])
def api_get_prompt_builder_wildcards():
    """獲取所有 wildcard 分類和內容，用於 Prompt Builder"""
    try:
        categories = sorted(
            Category.query.order_by(Category.level).all(),
            key=lambda c: (c.level, (c.display_name or c.name or ''))
        )

        result = []
        for category in categories:
            wildcards = Wildcard.query.filter_by(
                category_id=category.id,
                is_active=True
            ).order_by(Wildcard.content).all()

            if wildcards:
                result.append({
                    'id': category.id,
                    'name': category.name,
                    'display_name': category.display_name,
                    'full_path': category.get_full_path(),
                    'wildcard_path': _impact_wildcard_path(category.name),
                    'color': category.color,
                    'level': category.level,
                    'parent_id': category.parent_id,
                    'wildcard_count': len(wildcards),
                    'wildcards': [
                        {
                            'id': w.id,
                            'content': w.content,
                            'content_zh': w.content_zh
                        } for w in wildcards
                    ]
                })

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@pages_bp.route('/api/prompt-builder/preview', methods=['POST'])
def api_preview_prompt():
    """預覽提示詞 - 隨機化 wildcard 語法，支援變數"""
    data = request.json
    prompt_template = data.get('prompt', '')

    if not prompt_template:
        return jsonify({'error': '提示詞不能為空'}), 400

    try:
        variables = {}

        def replace_category_wildcard(match):
            wildcard_path = match.group(1)

            # Support both formats:
            #   __clothing/dress__  (ImpactWildcard YAML nested format)
            #   __clothing_dress__  (flat name format)
            #   __clothing-dress__  (legacy dash format)
            category_name = _name_from_impact_path(wildcard_path)  # slash → underscore
            category_name = category_name.replace('-', '_')         # dash → underscore

            category = Category.query.filter_by(name=category_name).first()
            if not category:
                # Fallback: try exact match on wildcard_path as name
                category = Category.query.filter_by(name=wildcard_path).first()
            if category:
                wildcards = Wildcard.query.filter_by(
                    category_id=category.id,
                    is_active=True
                ).all()
                if wildcards:
                    selected = random.choice(wildcards)
                    return selected.content
            return match.group(0)

        def replace_variable_definition(match):
            var_name = match.group(1)
            var_value = match.group(2)

            processed_value = var_value
            processed_value = re.sub(r'__([a-zA-Z0-9_/\-]+)__', replace_category_wildcard, processed_value)

            if '|' in processed_value:
                options = processed_value.split('|')
                processed_value = random.choice(options).strip()

            variables[var_name] = processed_value
            return processed_value

        def replace_variable_reference(match):
            var_name = match.group(1)
            return variables.get(var_name, match.group(0))

        def replace_choice_wildcard(match):
            full_match = match.group(0)
            content = match.group(1)

            if content.startswith('$') and '=' in content:
                return full_match

            options = content.split('|')
            return random.choice(options).strip()

        result = prompt_template
        max_iterations = 10

        for _ in range(max_iterations):
            old_result = result
            result = re.sub(r'\{\$([a-zA-Z0-9_]+)=([^}]+)\}', replace_variable_definition, result)
            if result == old_result:
                break

        for _ in range(max_iterations):
            old_result = result
            result = re.sub(r'__([a-zA-Z0-9_/\-]+)__', replace_category_wildcard, result)
            if result == old_result:
                break

        for _ in range(max_iterations):
            old_result = result
            result = re.sub(r'\{([^}]+)\}', replace_choice_wildcard, result)
            if result == old_result:
                break

        for _ in range(max_iterations):
            old_result = result
            result = re.sub(r'\$([a-zA-Z0-9_]+)', replace_variable_reference, result)
            if result == old_result:
                break

        return jsonify({
            'original': prompt_template,
            'preview': result,
            'variables': variables
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
