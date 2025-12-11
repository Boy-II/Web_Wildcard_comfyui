# -*- coding: utf-8 -*-
"""
Ollama 整合助手 - 使用本地 Ollama qwen3:8b 模型
用於：1. 翻譯 wildcard 內容  2. 智能分類協助
"""

import requests
import json
import time
from typing import Optional, Dict, List
import concurrent.futures


class OllamaHelper:
    """Ollama API 助手類"""

    def __init__(self, base_url, model="qwen:8b"):
        """
        初始化 Ollama API 助手
        :param base_url: Ollama 服務的基礎 URL (例如: http://host.docker.internal:11434)
        :param model: 要使用的模型名稱
        """
        if not base_url:
            raise ValueError("Ollama base_url 必須被提供")
        
        self.base_url = base_url
        self.model = model
        self.api_url = f"{self.base_url}/api/generate" # Fallback to generate endpoint

    def generate(self, prompt: str, system_prompt: str = None, max_retries=3, temperature: float = 0.3) -> Optional[str]:
        """
        呼叫 Ollama API (/api/generate) 生成回應

        Args:
            prompt: 用戶提示詞
            system_prompt: 系統提示詞
            max_retries: 最大重試次數
            temperature: 溫度參數 (0-2)，控制輸出的隨機性

        Returns:
            生成的文本或 None
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
            }
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')
                else:
                    print(f"Ollama API 錯誤: {response.status_code}")
                    print(f"錯誤內容: {response.text}")

            except requests.exceptions.RequestException as e:
                print(f"請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)

            except Exception as e:
                print(f"未預期的錯誤: {e}")
                break

        return None

    def translate_to_chinese(self, text: str, system_prompt: str, temperature: float = 0.3) -> Optional[str]:
        """
        將英文 wildcard 翻譯成中文

        Args:
            text: 要翻譯的英文文本
            system_prompt: 來自設定的系統提示詞
            temperature: 溫度參數 (0-2)，控制輸出的隨機性

        Returns:
            中文翻譯或 None
        """
        prompt = f"請將以下AI繪圖提示詞翻譯成繁體中文：\n{text}"

        return self.generate(prompt, system_prompt=system_prompt, temperature=temperature)

    def suggest_category(self, text: str, filename: str, available_categories: List[Dict]) -> Optional[str]:
        """
        使用 AI 建議最合適的分類

        Args:
            text: wildcard 內容
            filename: 檔案名稱
            available_categories: 可用的分類列表（包含路徑和描述）

        Returns:
            建議的分類路徑
        """
        # 構建分類選項字串
        categories_text = "\n".join([
            f"- {cat['full_path']}: {cat.get('description', '')}"
            for cat in available_categories
        ])

        system_prompt = """你是一個AI繪圖提示詞分類專家。
你的任務是根據提供的 wildcard 內容和檔案名稱，選擇最合適的分類。

規則：
1. 只返回分類的完整路徑（如：people/artists/anime_artists）
2. 不要返回任何解釋或其他文字
3. 選擇最具體、最精確的分類
4. 如果不確定，選擇較上層的分類"""

        prompt = f"""檔案名稱: {filename}
Wildcard 內容: {text}

可用分類:
{categories_text}

請選擇最合適的分類路徑:"""

        return self.generate(prompt, system_prompt)

    def batch_translate(self, texts: List[str], system_prompt: str, temperature: float = 0.3, max_workers=8) -> Dict[str, str]:
        """
        使用 ThreadPoolExecutor 實現平行批量翻譯
        Args:
            texts: 要翻譯的文本列表
            system_prompt: 系統提示詞
            temperature: 溫度
            max_workers: 最大平行工作執行緒數量
        Returns:
            翻譯結果字典 {原文: 譯文}
        """
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 建立原文和 future 的對應字典
            future_to_text = {executor.submit(self.translate_to_chinese, text, system_prompt, temperature): text for text in texts}
            
            print(f"開始平行翻譯 {len(texts)} 個項目 (使用 {max_workers} 個 workers)...")
            for i, future in enumerate(concurrent.futures.as_completed(future_to_text)):
                text = future_to_text[future]
                try:
                    translation = future.result()
                    if translation:
                        results[text] = translation
                    else:
                        results[text] = text # 翻譯失敗時保留原文
                    
                    print(f"翻譯進度: {i + 1}/{len(texts)}", end='\r')

                except Exception as exc:
                    print(f'\n{text} 產生例外: {exc}')
                    results[text] = text # 發生例外時也保留原文

        print("\n批次翻譯完成。")
        return results

    def check_connection(self) -> bool:
        """檢查 Ollama 服務是否可用"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def list_models(self) -> List[str]:
        """列出可用的模型"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except:
            pass
        return []
