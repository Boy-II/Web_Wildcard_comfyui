# -*- coding: utf-8 -*-
"""
資料庫模型定義
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Category(db.Model):
    """類別表 - 支援多層級樹狀結構"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(20), default='#6c757d')  # Bootstrap 顏色
    sort_order = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True, index=True)
    level = db.Column(db.Integer, default=0)  # 層級：0=根分類, 1=一級子分類, 2=二級子分類...
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    wildcards = db.relationship('Wildcard', back_populates='category', cascade='all, delete-orphan')

    # 自引用關聯：父子關係
    children = db.relationship('Category',
                              backref=db.backref('parent', remote_side=[id]),
                              cascade='all, delete-orphan')

    # 唯一約束：同一父分類下的子分類名稱不能重複
    __table_args__ = (
        db.UniqueConstraint('parent_id', 'name', name='uq_parent_name'),
        db.Index('idx_parent_sort', 'parent_id', 'sort_order'),
    )

    def __repr__(self):
        return f'<Category {self.get_full_path()}>'

    def get_full_path(self, separator=' > '):
        """獲取完整路徑（如：People > Artists > Anime Artists）"""
        path = [self.display_name]
        current = self
        while current.parent:
            current = current.parent
            path.insert(0, current.display_name)
        return separator.join(path)

    def get_wildcard_path(self):
        """獲取 Wildcard 語法路徑（使用 name，如：people-artists-anime_artists）"""
        path = [self.name]
        current = self
        while current.parent:
            current = current.parent
            path.insert(0, current.name)
        return '-'.join(path)

    def get_all_children(self, recursive=True):
        """獲取所有子分類"""
        if not recursive:
            return self.children

        result = []
        for child in self.children:
            result.append(child)
            result.extend(child.get_all_children(recursive=True))
        return result

    def get_all_wildcards(self, include_children=False):
        """獲取此分類的所有 wildcards，可選包含子分類"""
        if not include_children:
            return self.wildcards

        result = list(self.wildcards)
        for child in self.get_all_children(recursive=True):
            result.extend(child.wildcards)
        return result

    def to_dict(self, include_children=False, include_wildcards_count=True):
        """轉換為字典，可選包含子分類樹"""
        data = {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'color': self.color,
            'sort_order': self.sort_order,
            'parent_id': self.parent_id,
            'level': self.level,
            'full_path': self.get_full_path(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if include_wildcards_count:
            data['wildcard_count'] = len(self.wildcards)
            data['total_wildcard_count'] = len(self.get_all_wildcards(include_children=True))

        if include_children and self.children:
            data['children'] = [child.to_dict(include_children=True, include_wildcards_count=include_wildcards_count)
                               for child in sorted(self.children, key=lambda x: x.sort_order)]

        return data


class Wildcard(db.Model):
    """Wildcard 項目表"""
    __tablename__ = 'wildcards'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False, index=True)
    content_zh = db.Column(db.String(500))  # 中文翻譯
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    source_file = db.Column(db.String(255))  # 來源檔案名稱
    priority = db.Column(db.Integer, default=0)  # 權重/優先級
    is_active = db.Column(db.Boolean, default=True, index=True)  # 是否啟用
    tags = db.Column(db.String(500))  # 標籤（逗號分隔）
    notes = db.Column(db.Text)  # 備註
    translation_status = db.Column(db.String(20), default='pending')  # pending, translated, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    category = db.relationship('Category', back_populates='wildcards')

    # 唯一約束：同一類別中不能有重複的內容
    __table_args__ = (
        db.UniqueConstraint('category_id', 'content', name='uq_category_content'),
        db.Index('idx_content_active', 'content', 'is_active'),
    )

    def __repr__(self):
        return f'<Wildcard {self.content}>'

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'content_zh': self.content_zh,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'category_display_name': self.category.display_name if self.category else None,
            'category_full_path': self.category.get_full_path() if self.category else None,
            'source_file': self.source_file,
            'priority': self.priority,
            'is_active': self.is_active,
            'tags': self.tags.split(',') if self.tags else [],
            'notes': self.notes,
            'translation_status': self.translation_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ImportHistory(db.Model):
    """匯入歷史記錄表"""
    __tablename__ = 'import_history'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20))  # txt, zip
    items_imported = db.Column(db.Integer, default=0)
    items_skipped = db.Column(db.Integer, default=0)  # 重複跳過的數量
    status = db.Column(db.String(20))  # success, failed, partial
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ImportHistory {self.filename}>'

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'items_imported': self.items_imported,
            'items_skipped': self.items_skipped,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AppSetting(db.Model):
    """應用程式設定"""
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value
        }


class TranslationSetting(db.Model):
    """翻譯設定"""
    __tablename__ = 'translation_settings'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g., 'ollama', 'gemini'
    is_active = db.Column(db.Boolean, default=False, nullable=False, index=True)
    model_name = db.Column(db.String(100))
    temperature = db.Column(db.Float, default=0.3)
    system_prompt = db.Column(db.Text)
    api_key = db.Column(db.Text) # 加密儲存 (未來)

    def to_dict(self):
        return {
            "provider": self.provider,
            "is_active": self.is_active,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "system_prompt": self.system_prompt,
            # 安全起見，不直接回傳 api_key
            "has_api_key": bool(self.api_key)
        }


class PromptTemplate(db.Model):
    """提示詞模板"""
    __tablename__ = 'prompt_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PromptTemplate {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
