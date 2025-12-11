# -*- coding: utf-8 -*-
"""
智能自動分類器 - 根據檔案名稱自動匹配最合適的分類
"""

import re
from pathlib import Path


# 分類關鍵字映射表（從最具體到最一般）
CATEGORY_PATTERNS = [
    # ===== 人物 - People =====
    # 藝術家子分類
    ({'anime', 'manga'}, 'people/artists/anime_artists'),
    ({'photographer', 'photography'}, 'people/artists/photographers'),
    ({'director', 'film'}, 'people/artists/directors'),
    ({'concept'}, 'people/artists/concept_artists'),
    ({'comic', 'comicbook'}, 'people/artists/comic_artists'),
    ({'fineart', 'fine-art', 'painter'}, 'people/artists/fine_artists'),
    ({'digital', 'dig1', 'dig2', 'dig3'}, 'people/artists/digital_artists'),
    ({'artist', 'artist-', 'Artist'}, 'people/artists'),
    # 角色子分類
    ({'actor'}, 'people/characters/actors'),
    ({'actress'}, 'people/characters/actresses'),
    ({'character'}, 'people/characters/fictional_characters'),
    ({'celebrity', 'celeb'}, 'people/characters/celebrities'),

    # ===== 身體 - Body =====
    # 姿勢子分類
    ({'posture_arms', 'arm_pose'}, 'body/poses/arm_poses'),
    ({'posture_legs', 'leg_pose'}, 'body/poses/leg_poses'),
    ({'sitting', 'seated'}, 'body/poses/sitting'),
    ({'standing'}, 'body/poses/standing'),
    ({'lying', 'laying'}, 'body/poses/lying'),
    ({'action', 'dynamic'}, 'body/poses/action_poses'),
    ({'carrying', 'holding'}, 'body/poses/carrying_poses'),
    ({'posture', 'pose', 'poses'}, 'body/poses'),
    # 身體部位
    ({'face', 'facial', 'head'}, 'body/body_parts/head_face'),
    ({'hand', 'finger'}, 'body/body_parts/hands'),
    ({'leg', 'foot', 'feet'}, 'body/body_parts/legs'),
    ({'body', 'torso'}, 'body/body_parts'),
    # 其他身體相關
    ({'gesture'}, 'body/gestures'),
    ({'expression', 'emotion'}, 'body/expressions'),

    # ===== 服飾 - Clothing =====
    # 全身服裝子分類
    ({'dress', 'gown'}, 'clothing/full_outfits/dresses'),
    ({'uniform'}, 'clothing/full_outfits/uniforms'),
    ({'traditional', 'kimono', 'hanfu'}, 'clothing/full_outfits/traditional'),
    ({'swimwear', 'swimsuit', 'bikini'}, 'clothing/full_outfits/swimwear'),
    ({'wedding', 'bride'}, 'clothing/full_outfits/wedding'),
    ({'cosplay'}, 'clothing/full_outfits/cosplay'),
    # 配件子分類
    ({'hat', 'cap', 'headwear'}, 'clothing/accessories/hats'),
    ({'glasses', 'eyewear'}, 'clothing/accessories/glasses'),
    ({'jewelry', 'necklace', 'earring'}, 'clothing/accessories/jewelry'),
    ({'bag', 'purse'}, 'clothing/accessories/bags'),
    # 其他服飾
    ({'top', 'shirt', 'blouse'}, 'clothing/tops'),
    ({'bottom', 'pants', 'skirt'}, 'clothing/bottoms'),
    ({'underwear', 'lingerie', 'bra', 'panty'}, 'clothing/underwear'),
    ({'legwear', 'stockings', 'socks'}, 'clothing/legwear'),
    ({'footwear', 'shoes', 'boots'}, 'clothing/footwear'),
    ({'cloth', 'attire', 'outfit', 'wear'}, 'clothing'),

    # ===== 生物 - Creatures =====
    # 動物子分類
    ({'bird', 'avian'}, 'creatures/animals/birds'),
    ({'reptile', 'snake', 'lizard'}, 'creatures/animals/reptiles'),
    ({'insect', 'bug'}, 'creatures/animals/insects'),
    ({'mammal', 'cat', 'dog', 'animal'}, 'creatures/animals'),
    # 水生生物
    ({'fish'}, 'creatures/aquatic/fish'),
    ({'marine', 'sea', 'ocean'}, 'creatures/aquatic'),
    # 幻想生物
    ({'dragon'}, 'creatures/fantasy/dragons'),
    ({'angel'}, 'creatures/fantasy/angels'),
    ({'demon', 'devil'}, 'creatures/fantasy/demons'),
    ({'myth', 'legendary'}, 'creatures/fantasy/mythical'),
    # 其他生物
    ({'dinosaur', 'dino'}, 'creatures/dinosaurs'),
    ({'fantasy', 'creature'}, 'creatures/fantasy'),

    # ===== 場景/環境 - Scenes =====
    # 背景子分類
    ({'indoor', 'interior'}, 'scenes/backgrounds/indoor'),
    ({'outdoor', 'exterior'}, 'scenes/backgrounds/outdoor'),
    ({'nature', 'natural'}, 'scenes/backgrounds/nature'),
    ({'urban', 'city'}, 'scenes/backgrounds/urban'),
    ({'background', 'bg'}, 'scenes/backgrounds'),
    # 其他場景
    ({'location', 'place'}, 'scenes/locations'),
    ({'setting', 'environment'}, 'scenes/settings'),
    ({'decade', 'era', 'period'}, 'scenes/eras'),
    ({'weather', 'climate'}, 'scenes/weather'),
    ({'scene'}, 'scenes'),

    # ===== 藝術風格 - Art & Style =====
    # 藝術運動
    ({'art_nouveau', 'art-nouveau', 'nouveau'}, 'art_style/art_movements/art_nouveau'),
    ({'impressionism', 'impressionist'}, 'art_style/art_movements/impressionism'),
    ({'abstract'}, 'art_style/art_movements/abstract'),
    ({'modern_art', 'modernism'}, 'art_style/art_movements/modern_art'),
    ({'classical', 'renaissance'}, 'art_style/art_movements/classical_art'),
    ({'art-movement', 'movement'}, 'art_style/art_movements'),
    # 美學風格
    ({'anime', 'manga'}, 'art_style/aesthetic_styles/anime'),
    ({'realistic', 'realism'}, 'art_style/aesthetic_styles/realistic'),
    ({'cartoon', 'toon'}, 'art_style/aesthetic_styles/cartoon'),
    ({'cyberpunk', 'cyber'}, 'art_style/aesthetic_styles/cyberpunk'),
    ({'steampunk', 'steam'}, 'art_style/aesthetic_styles/steampunk'),
    # 主題風格
    ({'scifi', 'sci-fi', 'science fiction'}, 'art_style/theme_styles/scifi'),
    ({'fantasy'}, 'art_style/theme_styles/fantasy_style'),
    ({'horror', 'scary'}, 'art_style/theme_styles/horror'),
    ({'romance', 'romantic'}, 'art_style/theme_styles/romance'),
    # 一般風格
    ({'style', 'aesthetic'}, 'art_style/aesthetic_styles'),
    ({'art'}, 'art_style'),

    # ===== 技術 - Technical =====
    # 後製效果
    ({'filter'}, 'technical/post_processing/filters'),
    ({'aberration', 'chromatic'}, 'technical/post_processing/aberration'),
    ({'agfaphoto', 'kodak', 'fuji'}, 'technical/post_processing/brand_presets'),
    # 鏡頭/構圖
    ({'angle', 'view'}, 'technical/camera_composition/angles'),
    ({'lens'}, 'technical/camera_composition/lens_types'),
    ({'frame', 'framing'}, 'technical/camera_composition/framing'),
    ({'camera', 'composition'}, 'technical/camera_composition'),
    # 其他技術
    ({'3dengine', '3d-engine', 'unreal', 'unity'}, 'technical/3d_engines'),
    ({'render', 'rendering'}, 'technical/rendering'),
    ({'lighting', 'light'}, 'technical/lighting'),
    ({'3d', 'technical'}, 'technical'),

    # ===== 物件/道具 - Objects =====
    # 自然元素
    ({'plant', 'tree'}, 'objects/natural_elements/plants'),
    ({'flower', 'floral'}, 'objects/natural_elements/flowers'),
    ({'rock', 'stone', 'mineral'}, 'objects/natural_elements/rocks_minerals'),
    # 其他物件
    ({'food', 'cuisine'}, 'objects/food'),
    ({'vehicle', 'car', 'transport'}, 'objects/vehicles'),
    ({'weapon', 'sword', 'gun'}, 'objects/weapons'),
    ({'furniture'}, 'objects/furniture'),
    ({'object', 'item', 'prop'}, 'objects'),

    # ===== 形容詞 - Adjectives =====
    ({'adj-', 'adjective'}, 'adjectives/descriptive'),
    ({'emotion', 'mood'}, 'adjectives/emotional'),

    # ===== 顏色 - Colors =====
    ({'color', 'colour'}, 'colors/basic_colors'),

    # ===== 構圖 - Composition =====
    ({'focus'}, 'composition/focus'),
    ({'group'}, 'composition/groups'),
    ({'viewpoint'}, 'composition/viewpoint'),
    ({'composition'}, 'composition'),

    # ===== 其他分類 =====
    ({'audio', 'music', 'sound'}, 'audio'),
    ({'emoji'}, 'emoji'),
    ({'genre', 'pop-culture', 'pop_culture'}, 'pop_culture'),
    ({'game', 'gaming'}, 'pop_culture/games'),
]


def find_best_category(filename, from_webapp_models=False):
    """
    根據檔案名稱找出最合適的分類路徑

    Args:
        filename: 檔案名稱（含或不含副檔名）
        from_webapp_models: 是否從資料庫查詢並返回 Category 物件

    Returns:
        如果 from_webapp_models=True，返回 Category 物件
        否則返回分類路徑字串（如 'people/artists/anime_artists'）
    """
    # 移除副檔名和路徑
    name = Path(filename).stem.lower()

    # 遍歷所有模式，找出最匹配的
    for keywords, category_path in CATEGORY_PATTERNS:
        for keyword in keywords:
            if keyword.lower() in name:
                if from_webapp_models:
                    return get_category_by_path(category_path)
                return category_path

    # 預設返回「其他」分類
    if from_webapp_models:
        return get_category_by_path('misc')
    return 'misc'


def get_category_by_path(path):
    """
    根據路徑字串獲取 Category 物件
    例如: 'people/artists/anime_artists' -> Category 物件

    Args:
        path: 分類路徑，用 / 分隔

    Returns:
        Category 物件或 None
    """
    from webapp.models import Category

    parts = path.split('/')
    category = None

    # 逐層查找
    for part in parts:
        if category is None:
            # 查找根分類
            category = Category.query.filter_by(name=part, parent_id=None).first()
        else:
            # 查找子分類
            category = Category.query.filter_by(name=part, parent_id=category.id).first()

        if category is None:
            break

    return category


def get_category_suggestions(filename, top_n=3):
    """
    獲取多個可能的分類建議

    Args:
        filename: 檔案名稱
        top_n: 返回前 N 個建議

    Returns:
        分類路徑列表
    """
    name = Path(filename).stem.lower()
    suggestions = []

    for keywords, category_path in CATEGORY_PATTERNS:
        for keyword in keywords:
            if keyword.lower() in name:
                suggestions.append(category_path)
                if len(suggestions) >= top_n:
                    return suggestions

    # 如果沒找到足夠的建議，添加預設值
    if not suggestions:
        suggestions.append('misc')

    return suggestions


if __name__ == '__main__':
    # 測試
    test_files = [
        'artist-anime.txt',
        'pose.txt',
        'legwear.txt',
        'dragon.txt',
        'background.txt',
        'color.txt',
        '3dengines.txt',
        'food.txt',
        'adjectives.txt',
    ]

    print("自動分類測試：")
    print("-" * 60)
    for f in test_files:
        path = find_best_category(f)
        print(f"{f:30} -> {path}")
