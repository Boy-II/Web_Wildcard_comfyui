# -*- coding: utf-8 -*-
"""
初始化多層級分類結構
"""

# 完整的分類樹狀結構定義
CATEGORY_TREE = [
    {
        'name': 'people',
        'display_name': '人物',
        'color': '#007bff',
        'sort_order': 1,
        'description': '人物、藝術家、角色相關',
        'children': [
            {
                'name': 'artists',
                'display_name': '藝術家',
                'sort_order': 1,
                'description': '各類藝術創作者',
                'children': [
                    {'name': 'anime_artists', 'display_name': '動漫藝術家', 'sort_order': 1},
                    {'name': 'illustrators', 'display_name': '插畫家', 'sort_order': 2},
                    {'name': 'photographers', 'display_name': '攝影師', 'sort_order': 3},
                    {'name': 'directors', 'display_name': '導演', 'sort_order': 4},
                    {'name': 'concept_artists', 'display_name': '概念藝術家', 'sort_order': 5},
                    {'name': 'comic_artists', 'display_name': '漫畫家', 'sort_order': 6},
                    {'name': 'fine_artists', 'display_name': '美術藝術家', 'sort_order': 7},
                    {'name': 'digital_artists', 'display_name': '數位藝術家', 'sort_order': 8},
                    {'name': 'specialty_artists', 'display_name': '特殊風格藝術家', 'sort_order': 9},
                ]
            },
            {
                'name': 'characters',
                'display_name': '角色/名人',
                'sort_order': 2,
                'description': '演員、角色、名人',
                'children': [
                    {'name': 'actors', 'display_name': '演員', 'sort_order': 1},
                    {'name': 'actresses', 'display_name': '女演員', 'sort_order': 2},
                    {'name': 'fictional_characters', 'display_name': '虛構角色', 'sort_order': 3},
                    {'name': 'game_characters', 'display_name': '遊戲角色', 'sort_order': 4},
                    {'name': 'celebrities', 'display_name': '名人', 'sort_order': 5},
                ]
            },
        ]
    },
    {
        'name': 'body',
        'display_name': '身體',
        'color': '#28a745',
        'sort_order': 2,
        'description': '姿勢、身體部位、表情等',
        'children': [
            {
                'name': 'poses',
                'display_name': '姿勢',
                'sort_order': 1,
                'children': [
                    {'name': 'basic_poses', 'display_name': '基本姿勢', 'sort_order': 1},
                    {'name': 'arm_poses', 'display_name': '手臂姿勢', 'sort_order': 2},
                    {'name': 'leg_poses', 'display_name': '腿部姿勢', 'sort_order': 3},
                    {'name': 'sitting', 'display_name': '坐姿', 'sort_order': 4},
                    {'name': 'standing', 'display_name': '站姿', 'sort_order': 5},
                    {'name': 'lying', 'display_name': '躺姿', 'sort_order': 6},
                    {'name': 'action_poses', 'display_name': '動作姿勢', 'sort_order': 7},
                    {'name': 'carrying_poses', 'display_name': '攜帶姿勢', 'sort_order': 8},
                ]
            },
            {
                'name': 'body_parts',
                'display_name': '身體部位',
                'sort_order': 2,
                'children': [
                    {'name': 'head_face', 'display_name': '頭部/臉部', 'sort_order': 1},
                    {'name': 'hands', 'display_name': '手部', 'sort_order': 2},
                    {'name': 'legs', 'display_name': '腿部', 'sort_order': 3},
                    {'name': 'torso', 'display_name': '軀幹', 'sort_order': 4},
                ]
            },
            {'name': 'gestures', 'display_name': '手勢', 'sort_order': 3},
            {'name': 'expressions', 'display_name': '表情', 'sort_order': 4},
            {'name': 'body_features', 'display_name': '體型特徵', 'sort_order': 5},
        ]
    },
    {
        'name': 'clothing',
        'display_name': '服飾',
        'color': '#e83e8c',
        'sort_order': 3,
        'description': '服裝、配件等',
        'children': [
            {'name': 'tops', 'display_name': '上衣', 'sort_order': 1},
            {'name': 'bottoms', 'display_name': '下裝', 'sort_order': 2},
            {
                'name': 'full_outfits',
                'display_name': '全身服裝',
                'sort_order': 3,
                'children': [
                    {'name': 'dresses', 'display_name': '洋裝', 'sort_order': 1},
                    {'name': 'uniforms', 'display_name': '制服', 'sort_order': 2},
                    {'name': 'traditional', 'display_name': '傳統服飾', 'sort_order': 3},
                    {'name': 'swimwear', 'display_name': '泳裝', 'sort_order': 4},
                    {'name': 'wedding', 'display_name': '婚紗', 'sort_order': 5},
                    {'name': 'cosplay', 'display_name': 'Cosplay', 'sort_order': 6},
                ]
            },
            {'name': 'underwear', 'display_name': '內衣', 'sort_order': 4},
            {'name': 'legwear', 'display_name': '襪類', 'sort_order': 5},
            {
                'name': 'accessories',
                'display_name': '配件',
                'sort_order': 6,
                'children': [
                    {'name': 'hats', 'display_name': '帽子', 'sort_order': 1},
                    {'name': 'glasses', 'display_name': '眼鏡', 'sort_order': 2},
                    {'name': 'jewelry', 'display_name': '珠寶', 'sort_order': 3},
                    {'name': 'bags', 'display_name': '包包', 'sort_order': 4},
                ]
            },
            {'name': 'footwear', 'display_name': '鞋類', 'sort_order': 7},
        ]
    },
    {
        'name': 'creatures',
        'display_name': '生物',
        'color': '#fd7e14',
        'sort_order': 4,
        'description': '動物、幻想生物等',
        'children': [
            {
                'name': 'animals',
                'display_name': '動物',
                'sort_order': 1,
                'children': [
                    {'name': 'mammals', 'display_name': '哺乳類', 'sort_order': 1},
                    {'name': 'birds', 'display_name': '鳥類', 'sort_order': 2},
                    {'name': 'reptiles', 'display_name': '爬蟲類', 'sort_order': 3},
                    {'name': 'insects', 'display_name': '昆蟲', 'sort_order': 4},
                ]
            },
            {
                'name': 'aquatic',
                'display_name': '水生生物',
                'sort_order': 2,
                'children': [
                    {'name': 'fish', 'display_name': '魚類', 'sort_order': 1},
                    {'name': 'marine_life', 'display_name': '海洋生物', 'sort_order': 2},
                ]
            },
            {
                'name': 'fantasy',
                'display_name': '幻想生物',
                'sort_order': 3,
                'children': [
                    {'name': 'dragons', 'display_name': '龍', 'sort_order': 1},
                    {'name': 'angels', 'display_name': '天使', 'sort_order': 2},
                    {'name': 'demons', 'display_name': '惡魔', 'sort_order': 3},
                    {'name': 'mythical', 'display_name': '神話生物', 'sort_order': 4},
                ]
            },
            {'name': 'dinosaurs', 'display_name': '恐龍', 'sort_order': 4},
        ]
    },
    {
        'name': 'scenes',
        'display_name': '場景/環境',
        'color': '#ffc107',
        'sort_order': 5,
        'description': '背景、場景、環境設定',
        'children': [
            {
                'name': 'backgrounds',
                'display_name': '背景',
                'sort_order': 1,
                'children': [
                    {'name': 'indoor', 'display_name': '室內', 'sort_order': 1},
                    {'name': 'outdoor', 'display_name': '室外', 'sort_order': 2},
                    {'name': 'nature', 'display_name': '自然', 'sort_order': 3},
                    {'name': 'urban', 'display_name': '城市', 'sort_order': 4},
                ]
            },
            {'name': 'locations', 'display_name': '地點', 'sort_order': 2},
            {'name': 'settings', 'display_name': '環境設定', 'sort_order': 3},
            {'name': 'eras', 'display_name': '時代/年代', 'sort_order': 4},
            {'name': 'weather', 'display_name': '天氣/氣候', 'sort_order': 5},
        ]
    },
    {
        'name': 'art_style',
        'display_name': '藝術風格',
        'color': '#6f42c1',
        'sort_order': 6,
        'description': '藝術風格、美學、主題',
        'children': [
            {
                'name': 'art_movements',
                'display_name': '藝術運動',
                'sort_order': 1,
                'children': [
                    {'name': 'modern_art', 'display_name': '現代藝術', 'sort_order': 1},
                    {'name': 'classical_art', 'display_name': '古典藝術', 'sort_order': 2},
                    {'name': 'abstract', 'display_name': '抽象', 'sort_order': 3},
                    {'name': 'impressionism', 'display_name': '印象派', 'sort_order': 4},
                    {'name': 'art_nouveau', 'display_name': '新藝術', 'sort_order': 5},
                ]
            },
            {
                'name': 'aesthetic_styles',
                'display_name': '美學風格',
                'sort_order': 2,
                'children': [
                    {'name': 'anime', 'display_name': '動漫', 'sort_order': 1},
                    {'name': 'realistic', 'display_name': '寫實', 'sort_order': 2},
                    {'name': 'cartoon', 'display_name': '卡通', 'sort_order': 3},
                    {'name': 'cyberpunk', 'display_name': '賽博龐克', 'sort_order': 4},
                    {'name': 'steampunk', 'display_name': '蒸氣龐克', 'sort_order': 5},
                ]
            },
            {
                'name': 'theme_styles',
                'display_name': '主題風格',
                'sort_order': 3,
                'children': [
                    {'name': 'scifi', 'display_name': '科幻', 'sort_order': 1},
                    {'name': 'fantasy_style', 'display_name': '奇幻', 'sort_order': 2},
                    {'name': 'horror', 'display_name': '恐怖', 'sort_order': 3},
                    {'name': 'romance', 'display_name': '浪漫', 'sort_order': 4},
                ]
            },
        ]
    },
    {
        'name': 'technical',
        'display_name': '技術',
        'color': '#17a2b8',
        'sort_order': 7,
        'description': '3D、渲染、技術相關',
        'children': [
            {'name': '3d_engines', 'display_name': '3D 引擎', 'sort_order': 1},
            {'name': 'rendering', 'display_name': '渲染', 'sort_order': 2},
            {
                'name': 'camera_composition',
                'display_name': '鏡頭/構圖',
                'sort_order': 3,
                'children': [
                    {'name': 'angles', 'display_name': '視角', 'sort_order': 1},
                    {'name': 'lens_types', 'display_name': '鏡頭類型', 'sort_order': 2},
                    {'name': 'framing', 'display_name': '取景', 'sort_order': 3},
                ]
            },
            {'name': 'lighting', 'display_name': '燈光', 'sort_order': 4},
            {
                'name': 'post_processing',
                'display_name': '後製效果',
                'sort_order': 5,
                'children': [
                    {'name': 'filters', 'display_name': '濾鏡', 'sort_order': 1},
                    {'name': 'aberration', 'display_name': '色差', 'sort_order': 2},
                    {'name': 'brand_presets', 'display_name': '品牌預設', 'sort_order': 3},
                ]
            },
        ]
    },
    {
        'name': 'objects',
        'display_name': '物件/道具',
        'color': '#20c997',
        'sort_order': 8,
        'description': '各種物品、道具',
        'children': [
            {'name': 'food', 'display_name': '食物', 'sort_order': 1},
            {'name': 'vehicles', 'display_name': '交通工具', 'sort_order': 2},
            {'name': 'daily_items', 'display_name': '日常物品', 'sort_order': 3},
            {'name': 'weapons', 'display_name': '武器/裝備', 'sort_order': 4},
            {'name': 'furniture', 'display_name': '家具', 'sort_order': 5},
            {
                'name': 'natural_elements',
                'display_name': '自然元素',
                'sort_order': 6,
                'children': [
                    {'name': 'plants', 'display_name': '植物', 'sort_order': 1},
                    {'name': 'flowers', 'display_name': '花卉', 'sort_order': 2},
                    {'name': 'rocks_minerals', 'display_name': '石頭/礦物', 'sort_order': 3},
                ]
            },
        ]
    },
    {
        'name': 'adjectives',
        'display_name': '形容詞',
        'color': '#6610f2',
        'sort_order': 9,
        'description': '各類形容詞',
        'children': [
            {'name': 'emotional', 'display_name': '情緒形容詞', 'sort_order': 1},
            {'name': 'descriptive', 'display_name': '描述性形容詞', 'sort_order': 2},
            {'name': 'quality', 'display_name': '品質形容詞', 'sort_order': 3},
            {'name': 'appearance', 'display_name': '外觀形容詞', 'sort_order': 4},
        ]
    },
    {
        'name': 'colors',
        'display_name': '顏色',
        'color': '#dc3545',
        'sort_order': 10,
        'description': '顏色相關',
        'children': [
            {'name': 'basic_colors', 'display_name': '基本顏色', 'sort_order': 1},
            {'name': 'hues_tones', 'display_name': '色調/色相', 'sort_order': 2},
            {'name': 'color_combinations', 'display_name': '顏色組合', 'sort_order': 3},
        ]
    },
    {
        'name': 'composition',
        'display_name': '構圖',
        'color': '#198754',
        'sort_order': 11,
        'description': '構圖、視角、焦點',
        'children': [
            {'name': 'viewpoint', 'display_name': '視角', 'sort_order': 1},
            {'name': 'focus', 'display_name': '焦點', 'sort_order': 2},
            {'name': 'framing_crop', 'display_name': '框架/裁切', 'sort_order': 3},
            {'name': 'groups', 'display_name': '群組', 'sort_order': 4},
        ]
    },
    {
        'name': 'audio',
        'display_name': '音樂/音效',
        'color': '#0dcaf0',
        'sort_order': 12,
        'description': '音樂、音效相關',
        'children': [
            {'name': 'music_styles', 'display_name': '音樂風格', 'sort_order': 1},
            {'name': 'sound_effects', 'display_name': '音效描述', 'sort_order': 2},
        ]
    },
    {
        'name': 'culture',
        'display_name': '文化/地域',
        'color': '#ffc107',
        'sort_order': 13,
        'description': '文化、地域相關',
        'children': [
            {'name': 'countries', 'display_name': '國家/地區', 'sort_order': 1},
            {'name': 'cultural_elements', 'display_name': '文化元素', 'sort_order': 2},
            {'name': 'festivals', 'display_name': '節日/慶典', 'sort_order': 3},
        ]
    },
    {
        'name': 'pop_culture',
        'display_name': '流行文化',
        'color': '#d63384',
        'sort_order': 14,
        'description': '流行文化相關',
        'children': [
            {'name': 'movies_tv', 'display_name': '電影/電視', 'sort_order': 1},
            {'name': 'games', 'display_name': '遊戲', 'sort_order': 2},
            {'name': 'anime_manga', 'display_name': '動漫/漫畫', 'sort_order': 3},
            {'name': 'literature', 'display_name': '文學', 'sort_order': 4},
        ]
    },
    {
        'name': 'emoji',
        'display_name': '表情符號',
        'color': '#fd7e14',
        'sort_order': 15,
        'description': 'Emoji 相關',
    },
    {
        'name': 'misc',
        'display_name': '其他',
        'color': '#6c757d',
        'sort_order': 99,
        'description': '未分類項目',
    },
]


def create_category_tree(parent_category_data, parent_obj=None, level=0):
    """遞迴創建分類樹"""
    from webapp.models import db, Category

    # 創建當前分類
    category = Category(
        name=parent_category_data['name'],
        display_name=parent_category_data['display_name'],
        description=parent_category_data.get('description', ''),
        color=parent_category_data.get('color', '#6c757d'),
        sort_order=parent_category_data.get('sort_order', 0),
        parent_id=parent_obj.id if parent_obj else None,
        level=level
    )

    db.session.add(category)
    db.session.flush()  # 獲取 ID 但不提交

    # 遞迴創建子分類
    if 'children' in parent_category_data:
        for child_data in parent_category_data['children']:
            create_category_tree(child_data, category, level + 1)

    return category


def init_hierarchical_categories(app):
    """初始化完整的階層式分類"""
    from webapp.models import db, Category

    with app.app_context():
        # 檢查是否已有分類
        if Category.query.count() > 0:
            print(f"資料庫中已有 {Category.query.count()} 個分類")
            response = input("是否要清空並重建？(yes/no): ")
            if response.lower() != 'yes':
                print("取消重建")
                return

            # 清空現有分類
            Category.query.delete()
            db.session.commit()
            print("已清空現有分類")

        # 創建分類樹
        print("開始創建分類樹...")
        for root_data in CATEGORY_TREE:
            create_category_tree(root_data)

        db.session.commit()

        # 統計
        total = Category.query.count()
        root_count = Category.query.filter_by(level=0).count()
        print(f"\n✓ 分類創建完成！")
        print(f"  總計: {total} 個分類")
        print(f"  根分類: {root_count} 個")

        # 顯示分類樹
        print("\n分類樹結構:")
        for root in Category.query.filter_by(level=0).order_by(Category.sort_order):
            print_category_tree(root)


def print_category_tree(category, indent=0):
    """打印分類樹"""
    prefix = "  " * indent + ("└─ " if indent > 0 else "")
    print(f"{prefix}{category.display_name} ({category.name}) [L{category.level}]")

    for child in sorted(category.children, key=lambda x: x.sort_order):
        print_category_tree(child, indent + 1)


if __name__ == '__main__':
    from app import app
    init_hierarchical_categories(app)
