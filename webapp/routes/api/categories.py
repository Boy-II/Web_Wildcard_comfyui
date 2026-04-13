# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from webapp.models import db, Category
from webapp.services import category_service

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('', methods=['GET'])
def api_get_categories():
    """
    獲取所有類別
    Query參數:
      - tree: true/false - 是否返回樹狀結構（只返回根分類及其子分類）
      - flat: true/false - 返回扁平列表
      - parent_id: int - 只返回特定父分類的子分類
    """
    tree_mode = request.args.get('tree', 'false').lower() == 'true'
    parent_id = request.args.get('parent_id', type=int)

    if parent_id is not None:
        categories = Category.query.filter_by(parent_id=parent_id).order_by(Category.sort_order).all()
        return jsonify([cat.to_dict() for cat in categories])

    if tree_mode:
        root_categories = Category.query.filter_by(parent_id=None).order_by(Category.sort_order).all()
        return jsonify([cat.to_dict(include_children=True) for cat in root_categories])

    categories = Category.query.order_by(Category.level, Category.sort_order).all()
    return jsonify([cat.to_dict() for cat in categories])


@categories_bp.route('', methods=['POST'])
def api_create_category():
    """建立新類別"""
    data = request.json
    category = category_service.create_category(data)
    return jsonify(category.to_dict()), 201


@categories_bp.route('/<int:category_id>', methods=['PUT'])
def api_update_category(category_id):
    """更新類別，支援父類別變更和層級遞迴更新"""
    category = Category.query.get_or_404(category_id)
    data = request.json
    try:
        category = category_service.update_category(category, data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify(category.to_dict())


@categories_bp.route('/<int:category_id>', methods=['DELETE'])
def api_delete_category(category_id):
    """刪除類別（級聯刪除所有 wildcard 和子類別）"""
    category = Category.query.get_or_404(category_id)
    result = category_service.delete_category(category)
    return jsonify({
        'message': '類別已刪除',
        'deleted_wildcards': result['deleted_wildcards'],
        'deleted_children': result['deleted_children']
    }), 200
