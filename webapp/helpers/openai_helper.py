# -*- coding: utf-8 -*-
"""Generic OpenAI-compatible API helper.

Compatible with: OpenAI API, LM Studio, Ollama /v1 endpoint,
and any service implementing the OpenAI chat completions spec.

api_key may be empty string for local unauthenticated services.
"""

import requests
from typing import Optional
import concurrent.futures


class OpenAIHelper:
    def __init__(self, base_url: str, api_key: str = '', model: str = 'gpt-4o-mini'):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self._headers = {'Content-Type': 'application/json'}
        if api_key:
            self._headers['Authorization'] = f'Bearer {api_key}'

    def translate_to_chinese(
        self,
        text: str,
        system_prompt: str = '',
        temperature: float = 0.3,
    ) -> Optional[str]:
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text},
            ],
            'temperature': temperature,
        }
        try:
            resp = requests.post(
                f'{self.base_url}/chat/completions',
                json=payload,
                headers=self._headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f'[OpenAIHelper] translate error: {e}')
            return None

    def chat_messages(
        self,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Multi-turn chat with a full messages array."""
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
        }
        try:
            resp = requests.post(
                f'{self.base_url}/chat/completions',
                json=payload,
                headers=self._headers,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f'[OpenAIHelper] chat error: {e}')
            return None

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(
                f'{self.base_url}/models',
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return sorted([m['id'] for m in data.get('data', [])])
        except Exception as e:
            print(f'[OpenAIHelper] list_models error: {e}')
            return []

    def check_connection(self) -> bool:
        try:
            resp = requests.get(
                f'{self.base_url}/models',
                headers=self._headers,
                timeout=5,
            )
            return resp.status_code < 500
        except Exception:
            return False

    def batch_translate(
        self,
        texts: list[str],
        system_prompt: str = '',
        temperature: float = 0.3,
        max_workers: int = 8,
    ) -> list[Optional[str]]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.translate_to_chinese, t, system_prompt, temperature)
                for t in texts
            ]
            return [f.result() for f in futures]
