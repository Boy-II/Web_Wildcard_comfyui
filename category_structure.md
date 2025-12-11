# Wildcard 多層級分類架構設計

## 分類樹狀結構

### 1. 人物 (People)
- **藝術家 (Artists)**
  - 動漫藝術家 (Anime Artists)
  - 插畫家 (Illustrators)
  - 攝影師 (Photographers)
  - 導演 (Directors)
  - 概念藝術家 (Concept Artists)
  - 漫畫家 (Comic Artists)
  - 美術藝術家 (Fine Artists)
  - 特殊風格藝術家 (Specialty Artists)
- **角色/名人 (Characters/Celebrities)**
  - 演員 (Actors)
  - 女演員 (Actresses)
  - 虛構角色 (Fictional Characters)
  - 遊戲角色 (Game Characters)

### 2. 身體 (Body)
- **姿勢 (Poses)**
  - 基本姿勢 (Basic Poses)
  - 手臂姿勢 (Arm Poses)
  - 腿部姿勢 (Leg Poses)
  - 坐姿 (Sitting)
  - 站姿 (Standing)
  - 躺姿 (Lying)
  - 動作姿勢 (Action Poses)
  - 攜帶物品姿勢 (Carrying Poses)
- **身體部位 (Body Parts)**
  - 頭部/臉部 (Head/Face)
  - 手部 (Hands)
  - 腿部 (Legs)
  - 軀幹 (Torso)
- **手勢 (Gestures)**
- **表情 (Expressions)**
- **體型特徵 (Body Features)**

### 3. 服飾 (Clothing)
- **上衣 (Tops)**
- **下裝 (Bottoms)**
- **全身服裝 (Full Outfits)**
  - 洋裝 (Dresses)
  - 制服 (Uniforms)
  - 傳統服飾 (Traditional)
  - 泳裝 (Swimwear)
  - 婚紗 (Wedding)
- **內衣 (Underwear/Lingerie)**
- **襪類 (Legwear)**
- **配件 (Accessories)**
  - 帽子 (Hats)
  - 眼鏡 (Glasses)
  - 珠寶 (Jewelry)
  - 包包 (Bags)
- **鞋類 (Footwear)**

### 4. 生物 (Creatures)
- **動物 (Animals)**
  - 哺乳類 (Mammals)
  - 鳥類 (Birds)
  - 爬蟲類 (Reptiles)
  - 昆蟲 (Insects)
- **水生生物 (Aquatic)**
  - 魚類 (Fish)
  - 海洋生物 (Marine Life)
- **幻想生物 (Fantasy)**
  - 龍 (Dragons)
  - 天使 (Angels)
  - 惡魔 (Demons)
  - 神話生物 (Mythical)
- **恐龍 (Dinosaurs)**

### 5. 場景/環境 (Scenes/Environment)
- **背景 (Backgrounds)**
  - 室內 (Indoor)
  - 室外 (Outdoor)
  - 自然 (Nature)
  - 城市 (Urban)
- **地點 (Locations)**
- **環境設定 (Settings)**
- **時代/年代 (Eras/Decades)**
- **天氣/氣候 (Weather/Climate)**

### 6. 藝術風格 (Art & Style)
- **藝術運動 (Art Movements)**
  - 現代藝術 (Modern Art)
  - 古典藝術 (Classical Art)
  - 抽象 (Abstract)
  - 印象派 (Impressionism)
  - 新藝術 (Art Nouveau)
- **美學風格 (Aesthetic Styles)**
  - 動漫 (Anime)
  - 寫實 (Realistic)
  - 卡通 (Cartoon)
  - 賽博龐克 (Cyberpunk)
  - 蒸氣龐克 (Steampunk)
- **主題風格 (Theme Styles)**
  - 科幻 (Sci-Fi)
  - 奇幻 (Fantasy)
  - 恐怖 (Horror)
  - 浪漫 (Romance)

### 7. 技術 (Technical)
- **3D 引擎 (3D Engines)**
- **渲染 (Rendering)**
- **鏡頭/構圖 (Camera/Composition)**
  - 視角 (Angles)
  - 鏡頭類型 (Lens Types)
  - 取景 (Framing)
- **燈光 (Lighting)**
- **後製效果 (Post-Processing)**
  - 濾鏡 (Filters)
  - 色差 (Aberration)
  - 品牌預設 (Brand Presets)

### 8. 物件/道具 (Objects)
- **食物 (Food)**
- **交通工具 (Vehicles)**
- **日常物品 (Daily Items)**
- **武器/裝備 (Weapons/Equipment)**
- **家具 (Furniture)**
- **自然元素 (Natural Elements)**
  - 植物 (Plants)
  - 花卉 (Flowers)
  - 石頭/礦物 (Rocks/Minerals)

### 9. 形容詞 (Adjectives)
- **情緒形容詞 (Emotional)**
- **描述性形容詞 (Descriptive)**
- **品質形容詞 (Quality)**
- **外觀形容詞 (Appearance)**

### 10. 顏色 (Colors)
- **基本顏色 (Basic Colors)**
- **色調/色相 (Hues/Tones)**
- **顏色組合 (Color Combinations)**

### 11. 構圖 (Composition)
- **視角 (Viewpoint)**
- **焦點 (Focus)**
- **框架/裁切 (Framing)**
- **群組 (Groups)**

### 12. 音樂/音效 (Audio)
- **音樂風格 (Music Styles)**
- **音效描述 (Sound Effects)**

### 13. 文化/地域 (Culture/Region)
- **國家/地區 (Countries/Regions)**
- **文化元素 (Cultural Elements)**
- **節日/慶典 (Festivals/Celebrations)**

### 14. 流行文化 (Pop Culture)
- **電影/電視 (Movies/TV)**
- **遊戲 (Games)**
- **動漫/漫畫 (Anime/Manga)**
- **文學 (Literature)**

### 15. 表情符號 (Emoji)

### 16. 其他 (Miscellaneous)

## 檔案名稱對應規則

### 人物類
- `actor*.txt`, `actress*.txt` → People > Characters/Celebrities > Actors/Actresses
- `artist*.txt`, `Artist*.txt` → People > Artists
- `artist-anime*.txt` → People > Artists > Anime Artists
- `artist-photographer*.txt` → People > Artists > Photographers
- `artist-director*.txt` → People > Artists > Directors
- `character*.txt` → People > Characters/Celebrities > Fictional Characters

### 身體類
- `pose*.txt`, `posture*.txt` → Body > Poses
- `gesture*.txt` → Body > Gestures
- `body*.txt` → Body > Body Parts
- `face*.txt`, `facial*.txt` → Body > Body Parts > Head/Face
- `hand*.txt` → Body > Body Parts > Hands

### 服飾類
- `cloth*.txt`, `attire*.txt` → Clothing
- `legwear*.txt` → Clothing > Legwear
- `underwear*.txt`, `lingerie*.txt` → Clothing > Underwear

### 生物類
- `animal*.txt` → Creatures > Animals
- `bird*.txt` → Creatures > Animals > Birds
- `fish*.txt` → Creatures > Aquatic > Fish
- `dragon*.txt` → Creatures > Fantasy > Dragons
- `angel*.txt` → Creatures > Fantasy > Angels
- `dinosaur*.txt` → Creatures > Dinosaurs

### 場景類
- `background*.txt`, `scene*.txt` → Scenes/Environment > Backgrounds
- `location*.txt`, `setting*.txt` → Scenes/Environment > Locations
- `environment*.txt` → Scenes/Environment
- `decade*.txt` → Scenes/Environment > Eras/Decades

### 藝術風格類
- `style*.txt`, `aesthetic*.txt` → Art & Style > Aesthetic Styles
- `art-movement*.txt`, `art_nouveau*.txt` → Art & Style > Art Movements
- `anime*.txt` → Art & Style > Aesthetic Styles > Anime
- `scifi*.txt`, `sci-fi*.txt` → Art & Style > Theme Styles > Sci-Fi
- `fantasy*.txt` → Art & Style > Theme Styles > Fantasy
- `horror*.txt` → Art & Style > Theme Styles > Horror

### 技術類
- `3d*.txt`, `3dengine*.txt` → Technical > 3D Engines
- `render*.txt` → Technical > Rendering
- `camera*.txt` → Technical > Camera/Composition
- `lighting*.txt`, `light*.txt` → Technical > Lighting
- `aberration*.txt` → Technical > Post-Processing > Aberration

### 物件類
- `object*.txt`, `item*.txt`, `prop*.txt` → Objects
- `food*.txt` → Objects > Food
- `vehicle*.txt` → Objects > Vehicles

### 形容詞類
- `adj*.txt`, `adjective*.txt` → Adjectives > Descriptive

### 顏色類
- `color*.txt`, `colour*.txt` → Colors > Basic Colors

### 構圖類
- `composition*.txt` → Composition
- `focus*.txt` → Composition > Focus
- `group*.txt` → Composition > Groups

### 其他
- `audio*.txt` → Audio
- `emoji*.txt` → Emoji
- `genre*.txt` → Pop Culture
- `games*.txt` → Pop Culture > Games
- `pop-culture*.txt` → Pop Culture
