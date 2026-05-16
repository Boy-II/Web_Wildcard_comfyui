# -*- coding: utf-8 -*-
"""
ComfyUI REST API client.

Connects to a running ComfyUI instance (default: http://192.168.1.180:8188).
The base URL can be overridden via AppSetting key 'comfyui_api_url'.
"""

import uuid
import requests

COMFYUI_DEFAULT_URL = 'http://192.168.1.180:8188'
_TIMEOUT_SHORT = 5
_TIMEOUT_LONG = 30


def get_comfyui_url() -> str:
    from webapp.models import AppSetting
    setting = AppSetting.query.filter_by(key='comfyui_api_url').first()
    if setting and setting.value:
        return setting.value.rstrip('/')
    return COMFYUI_DEFAULT_URL


def check_connection() -> tuple[bool, dict]:
    """Return (is_connected, info_dict). Never raises."""
    try:
        r = requests.get(f'{get_comfyui_url()}/system_stats', timeout=_TIMEOUT_SHORT)
        return r.ok, r.json() if r.ok else {}
    except Exception as e:
        return False, {'error': str(e)}


def queue_prompt(workflow: dict) -> dict:
    """
    POST /prompt to ComfyUI.
    Returns the ComfyUI response dict (keys: prompt_id, number, node_errors).
    Raises requests.HTTPError or requests.ConnectionError on failure.
    """
    client_id = str(uuid.uuid4())
    payload = {'prompt': workflow, 'client_id': client_id}
    r = requests.post(f'{get_comfyui_url()}/prompt', json=payload, timeout=_TIMEOUT_LONG)
    r.raise_for_status()
    return r.json()


def get_history(prompt_id: str) -> dict:
    """
    GET /history/{prompt_id}.
    Returns {} while the job is still queued/running.
    Returns {prompt_id: {status, outputs, ...}} when done.
    """
    r = requests.get(f'{get_comfyui_url()}/history/{prompt_id}', timeout=_TIMEOUT_SHORT)
    r.raise_for_status()
    return r.json()


def get_image_bytes(filename: str, subfolder: str = '', folder_type: str = 'output') -> tuple[bytes, str]:
    """
    GET /view and return (raw_bytes, content_type).
    """
    params = {'filename': filename, 'subfolder': subfolder, 'type': folder_type}
    r = requests.get(f'{get_comfyui_url()}/view', params=params, timeout=_TIMEOUT_LONG)
    r.raise_for_status()
    return r.content, r.headers.get('Content-Type', 'image/png')


def get_queue() -> dict:
    """GET /queue — returns pending/running queue info."""
    r = requests.get(f'{get_comfyui_url()}/queue', timeout=_TIMEOUT_SHORT)
    r.raise_for_status()
    return r.json()
