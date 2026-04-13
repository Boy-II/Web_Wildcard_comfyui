# -*- coding: utf-8 -*-
"""
Google Gemini API 整合助手
"""
import os
from typing import Optional, List, Dict
import google.generativeai as genai
import concurrent.futures

class GeminiHelper:
    """Gemini API 助手類"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro-preview-0514"):
        if not api_key:
            raise ValueError("Gemini API Key 必須被提供")
        
        genai.configure(api_key=api_key)
        
        self.model_name = model
        # 設定安全設定以避免被阻擋
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        self.model = genai.GenerativeModel(self.model_name, safety_settings=self.safety_settings)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> Optional[str]:
        """
        使用 Gemini API 生成回應

        Args:
            prompt: 用戶提示詞
            system_prompt: 系統提示詞
            temperature: 溫度參數 (0-1)，控制輸出的隨機性

        Returns:
            生成的文本或 None
        """
        try:
            # Gemini API v1beta 將 system instruction 與 messages 分開
            full_prompt = [prompt]
            if system_prompt:
                # 將系統提示詞加到用戶提示詞前面
                full_prompt.insert(0, system_prompt)

            generation_config = genai.types.GenerationConfig(temperature=temperature)

            response = self.model.generate_content(full_prompt, generation_config=generation_config)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API 錯誤: {e}", flush=True)
            return None

    def translate_to_chinese(self, text: str, system_prompt: str, temperature: float = 0.3) -> Optional[str]:
        """
        將英文 wildcard 翻譯成中文

        Args:
            text: 要翻譯的英文文本
            system_prompt: 來自設定的系統提示詞
            temperature: 溫度參數 (0-1)，控制輸出的隨機性

        Returns:
            中文翻譯或 None
        """
        prompt = f"請將以下AI繪圖提示詞翻譯成繁體中文：\n'{text}'"
        return self.generate(prompt, system_prompt, temperature)

    def batch_translate(self, texts: List[str], system_prompt: str, temperature: float = 0.3, max_workers=8) -> Dict[str, str]:
        """
        使用 ThreadPoolExecutor 實現平行批量翻譯
        """
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_text = {executor.submit(self.translate_to_chinese, text, system_prompt, temperature): text for text in texts}
            
            print(f"開始使用 Gemini 平行翻譯 {len(texts)} 個項目...")
            for i, future in enumerate(concurrent.futures.as_completed(future_to_text)):
                text = future_to_text[future]
                try:
                    translation = future.result()
                    if translation:
                        results[text] = translation
                    else:
                        results[text] = text
                    
                    print(f"翻譯進度: {i + 1}/{len(texts)}", end='\r')

                except Exception as exc:
                    print(f'\n{text} 產生例外: {exc}')
                    results[text] = text

        print("\nGemini 批次翻譯完成。")
        return results

    @staticmethod
    def check_api_key(api_key: str) -> bool:
        """檢查 API Key 是否有效"""
        if not api_key:
            return False
        try:
            genai.configure(api_key=api_key)
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            return len(models) > 0
        except Exception as e:
            print(f"檢查 Gemini API Key 時發生錯誤: {e}")
            return False
