# -*- coding: utf-8 -*-
"""
Pollinations API 整合助手 - 使用 Pollinations.ai 雲端模型
用於：1. 翻譯 wildcard 內容  2. 智能分類協助
"""

import requests
import json
import time
from typing import Optional, Dict, List
import concurrent.futures


class PollinationsHelper:
    """Pollinations API 助手類"""

    def __init__(self, api_key: str = None, model: str = "openai", base_url: str = "https://text.pollinations.ai"):
        """
        初始化 Pollinations API 助手

        Args:
            api_key: Pollinations API 金鑰（可選，用於高級功能）
            model: 要使用的模型名稱（openai, mistral, searchgpt等）
            base_url: Pollinations API 基礎 URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.openai_endpoint = f"{base_url}/openai"
        self.simple_endpoint = base_url

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = None
    ) -> Optional[str]:
        """
        呼叫 Pollinations API 生成回應（使用 OpenAI 格式）

        Args:
            prompt: 用戶提示詞
            system_prompt: 系統提示詞
            max_retries: 最大重試次數
            temperature: 溫度參數 (0-3)，控制輸出的創造性
            max_tokens: 最大 token 數

        Returns:
            生成的文本或 None
        """
        # 構建 messages 格式
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Content-Type": "application/json"
        }

        # 如果有 API key，加入 headers
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.openai_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    # 處理 OpenAI 格式的響應
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    return result.get("response", "")
                else:
                    print(f"Pollinations API 錯誤: {response.status_code}")
                    print(f"錯誤內容: {response.text}")

            except requests.exceptions.RequestException as e:
                print(f"請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 比本地 Ollama 多等一點時間

            except Exception as e:
                print(f"未預期的錯誤: {e}")
                break

        return None

    def generate_simple(
        self,
        prompt: str,
        max_retries: int = 3,
        temperature: float = 0.7,
        system: str = None
    ) -> Optional[str]:
        """
        使用簡單的 GET 方式呼叫 API

        Args:
            prompt: 用戶提示詞
            max_retries: 最大重試次數
            temperature: 溫度參數
            system: 系統提示詞

        Returns:
            生成的文本或 None
        """
        params = {
            "model": self.model,
            "temperature": temperature
        }

        if system:
            params["system"] = system

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(max_retries):
            try:
                # 使用 GET 方式，prompt 作為 URL 的一部分
                url = f"{self.simple_endpoint}/{requests.utils.quote(prompt)}"

                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=60
                )

                if response.status_code == 200:
                    return response.text
                else:
                    print(f"Pollinations API 錯誤: {response.status_code}")
                    print(f"錯誤內容: {response.text}")

            except requests.exceptions.RequestException as e:
                print(f"請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)

            except Exception as e:
                print(f"未預期的錯誤: {e}")
                break

        return None

    def translate_to_chinese(
        self,
        text: str,
        system_prompt: str = None,
        temperature: float = 1.0
    ) -> Optional[str]:
        """
        將英文 wildcard 翻譯成中文

        Args:
            text: 要翻譯的英文文本
            system_prompt: 系統提示詞
            temperature: 溫度參數（固定為 1.0，Pollinations 限制）

        Returns:
            中文翻譯或 None
        """
        if not system_prompt:
            system_prompt = "你是一個專業的AI繪圖提示詞翻譯助手。請將英文提示詞準確翻譯成繁體中文，保持專業術語的準確性。"

        prompt = f"請將以下AI繪圖提示詞翻譯成繁體中文，只返回翻譯結果，不要添加解釋：\n{text}"

        # Pollinations 模型強制使用 temperature=1.0
        return self.generate(prompt, system_prompt=system_prompt, temperature=1.0)

    def suggest_category(
        self,
        text: str,
        filename: str,
        available_categories: List[Dict]
    ) -> Optional[str]:
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

    def batch_translate(
        self,
        texts: List[str],
        system_prompt: str = None,
        temperature: float = 1.0,
        max_workers: int = 5
    ) -> Dict[str, str]:
        """
        使用 ThreadPoolExecutor 實現平行批量翻譯

        注意：雲端 API 使用較少的 workers 避免觸發速率限制

        Args:
            texts: 要翻譯的文本列表
            system_prompt: 系統提示詞
            temperature: 溫度（固定為 1.0，Pollinations 限制）
            max_workers: 最大平行工作執行緒數量（建議 3-5）

        Returns:
            翻譯結果字典 {原文: 譯文}
        """
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 建立原文和 future 的對應字典（temperature 固定為 1.0）
            future_to_text = {
                executor.submit(self.translate_to_chinese, text, system_prompt, 1.0): text
                for text in texts
            }

            print(f"開始平行翻譯 {len(texts)} 個項目 (使用 {max_workers} 個 workers)...")
            completed = 0

            for future in concurrent.futures.as_completed(future_to_text):
                text = future_to_text[future]
                try:
                    translation = future.result()
                    if translation:
                        results[text] = translation
                    else:
                        results[text] = text  # 翻譯失敗時保留原文

                    completed += 1
                    print(f"翻譯進度: {completed}/{len(texts)}", end='\r')

                    # 添加延遲避免速率限制
                    time.sleep(0.5)

                except Exception as exc:
                    print(f'\n{text} 產生例外: {exc}')
                    results[text] = text  # 發生例外時也保留原文

        print("\n批次翻譯完成。")
        return results

    def check_connection(self) -> bool:
        """檢查 Pollinations 服務是否可用"""
        try:
            # 嘗試獲取模型列表
            response = requests.get(f"{self.base_url}/models", timeout=10)
            return response.status_code == 200
        except:
            return False

    def list_models(self) -> List[str]:
        """列出可用的模型"""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Pollinations 返回的是物件數組，需要提取 'name' 欄位
                if isinstance(data, list):
                    model_names = []
                    for model in data:
                        if isinstance(model, dict):
                            # 提取 'name' 欄位
                            name = model.get('name', '')
                            if name:
                                model_names.append(name)
                        else:
                            model_names.append(str(model))
                    return model_names
                return []
        except Exception as e:
            print(f"獲取模型列表失敗: {e}")
        return []

    def get_model_info(self) -> Dict:
        """獲取當前使用的模型資訊"""
        return {
            "provider": "Pollinations.ai",
            "model": self.model,
            "base_url": self.base_url,
            "has_api_key": bool(self.api_key)
        }
