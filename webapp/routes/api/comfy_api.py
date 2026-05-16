# -*- coding: utf-8 -*-
"""
ComfyUI Workflow API Blueprint.

Endpoints:
  GET  /api/comfy/status                      — check ComfyUI connection
  GET|PUT /api/comfy/url                      — read/write ComfyUI base URL
  GET  /api/comfy/workflows                   — list saved workflows
  POST /api/comfy/workflows                   — create workflow
  GET  /api/comfy/workflows/<id>              — get workflow (with JSON)
  PUT  /api/comfy/workflows/<id>              — update workflow
  DEL  /api/comfy/workflows/<id>              — delete workflow
  POST /api/comfy/workflows/<id>/run          — queue execution
  GET  /api/comfy/workflows/<id>/jobs         — list recent jobs for a workflow
  GET  /api/comfy/jobs/<id>/status            — poll job status (syncs with ComfyUI)
  GET  /api/comfy/jobs/<id>/image             — proxy image from ComfyUI
"""

import io
import json
import random
from datetime import datetime

import requests as _requests
from flask import Blueprint, request, jsonify, send_file
from webapp.models import db, AppSetting, ComfyWorkflow, ComfyJob
from webapp.services import comfy_api_service

comfy_api_bp = Blueprint('comfy_api', __name__)


# ── Connection & config ──────────────────────────────────────

@comfy_api_bp.route('/status')
def api_comfy_status():
    ok, info = comfy_api_service.check_connection()
    return jsonify({'connected': ok, 'url': comfy_api_service.get_comfyui_url(), 'info': info})


@comfy_api_bp.route('/url', methods=['GET', 'PUT'])
def api_comfy_url():
    if request.method == 'GET':
        return jsonify({'url': comfy_api_service.get_comfyui_url()})

    data = request.json or {}
    url = data.get('url', '').strip().rstrip('/')
    if not url:
        return jsonify({'error': '請提供 URL'}), 400

    setting = AppSetting.query.filter_by(key='comfyui_api_url').first()
    if setting:
        setting.value = url
    else:
        db.session.add(AppSetting(key='comfyui_api_url', value=url))
    db.session.commit()
    return jsonify({'url': url})


# ── Model list ───────────────────────────────────────────────

@comfy_api_bp.route('/models', methods=['GET'])
def api_comfy_models():
    """
    Fetch available checkpoint model names from ComfyUI.
    GET /object_info/CheckpointLoaderSimple and extract ckpt_name list.
    """
    node_type = request.args.get('node', 'CheckpointLoaderSimple')
    field     = request.args.get('field', 'ckpt_name')
    try:
        r = _requests.get(
            f'{comfy_api_service.get_comfyui_url()}/object_info/{node_type}',
            timeout=10,
        )
        r.raise_for_status()
        data       = r.json()
        node_info  = data.get(node_type, {})
        required   = node_info.get('input', {}).get('required', {})
        field_data = required.get(field, [])
        # ComfyUI returns [[list_of_values], {options_dict}]
        if field_data and isinstance(field_data[0], list):
            return jsonify(sorted(field_data[0]))
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 502


# ── Workflow CRUD ────────────────────────────────────────────

@comfy_api_bp.route('/workflows', methods=['GET'])
def api_list_workflows():
    workflows = ComfyWorkflow.query.order_by(ComfyWorkflow.updated_at.desc()).all()
    return jsonify([w.to_dict() for w in workflows])


@comfy_api_bp.route('/workflows', methods=['POST'])
def api_create_workflow():
    data = request.json or {}
    name = data.get('name', '').strip()
    wj = data.get('workflow_json', '')

    if not name:
        return jsonify({'error': '請提供名稱'}), 400
    if not wj:
        return jsonify({'error': '請提供 Workflow JSON'}), 400

    wj_str = _validate_and_stringify(wj)
    if wj_str is None:
        return jsonify({'error': 'JSON 格式錯誤'}), 400

    w = ComfyWorkflow(name=name, description=data.get('description', ''), workflow_json=wj_str)
    db.session.add(w)
    db.session.commit()
    return jsonify(w.to_dict(include_json=True)), 201


@comfy_api_bp.route('/workflows/<int:wid>', methods=['GET'])
def api_get_workflow(wid):
    w = ComfyWorkflow.query.get_or_404(wid)
    return jsonify(w.to_dict(include_json=True))


@comfy_api_bp.route('/workflows/<int:wid>', methods=['PUT'])
def api_update_workflow(wid):
    w = ComfyWorkflow.query.get_or_404(wid)
    data = request.json or {}

    if 'name' in data:
        w.name = data['name'].strip()
    if 'description' in data:
        w.description = data['description']
    if 'workflow_json' in data:
        wj_str = _validate_and_stringify(data['workflow_json'])
        if wj_str is None:
            return jsonify({'error': 'JSON 格式錯誤'}), 400
        w.workflow_json = wj_str

    db.session.commit()
    return jsonify(w.to_dict(include_json=True))


@comfy_api_bp.route('/workflows/<int:wid>', methods=['DELETE'])
def api_delete_workflow(wid):
    w = ComfyWorkflow.query.get_or_404(wid)
    db.session.delete(w)
    db.session.commit()
    return jsonify({'message': '已刪除'})


# ── Execution ────────────────────────────────────────────────

@comfy_api_bp.route('/workflows/<int:wid>/run', methods=['POST'])
def api_run_workflow(wid):
    w = ComfyWorkflow.query.get_or_404(wid)
    data = request.json or {}
    placeholders = dict(data.get('placeholders', {}))   # mutable copy

    # Resolve seed=-1 to a random value before substitution
    resolved_seed = None
    if 'seed' in placeholders:
        try:
            seed_val = int(placeholders['seed'])
            if seed_val == -1:
                seed_val = random.randint(0, 2 ** 32 - 1)
            placeholders['seed'] = seed_val
            resolved_seed = seed_val
        except (ValueError, TypeError):
            pass

    # Apply placeholder substitution on the raw JSON string before parsing
    wf_str = _apply_placeholders(w.workflow_json, placeholders)

    try:
        workflow = json.loads(wf_str)
    except json.JSONDecodeError as e:
        return jsonify({'error': f'替換佔位符後 JSON 格式錯誤: {e}'}), 400

    # Create job record first so we always have an ID to return
    job = ComfyJob(workflow_id=wid, status='queued')
    db.session.add(job)
    db.session.flush()

    try:
        result = comfy_api_service.queue_prompt(workflow)
        node_errors = result.get('node_errors', {})
        if node_errors:
            job.status = 'failed'
            job.error_message = f'節點錯誤: {json.dumps(node_errors, ensure_ascii=False)}'
            db.session.commit()
            return jsonify({'error': job.error_message}), 422

        job.prompt_id = result.get('prompt_id')
        job.status = 'running'
        db.session.commit()
        return jsonify({
            'job_id': job.id,
            'prompt_id': job.prompt_id,
            'resolved_seed': resolved_seed,   # None if seed wasn't -1
        })

    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        db.session.commit()
        return jsonify({'error': str(e)}), 500


# ── Job status & history ─────────────────────────────────────

@comfy_api_bp.route('/workflows/<int:wid>/jobs', methods=['GET'])
def api_workflow_jobs(wid):
    ComfyWorkflow.query.get_or_404(wid)
    jobs = (ComfyJob.query
            .filter_by(workflow_id=wid)
            .order_by(ComfyJob.created_at.desc())
            .limit(30)
            .all())
    return jsonify([j.to_dict() for j in jobs])


@comfy_api_bp.route('/jobs/<int:jid>/status', methods=['GET'])
def api_job_status(jid):
    job = ComfyJob.query.get_or_404(jid)

    if job.status in ('completed', 'failed') or not job.prompt_id:
        return jsonify(job.to_dict())

    try:
        history = comfy_api_service.get_history(job.prompt_id)
        if job.prompt_id in history:
            h = history[job.prompt_id]
            status_str = h.get('status', {}).get('status_str', '')

            if status_str == 'success':
                images = []
                for node_id, node_out in h.get('outputs', {}).items():
                    for img in node_out.get('images', []):
                        images.append({
                            'filename': img['filename'],
                            'subfolder': img.get('subfolder', ''),
                            'type': img.get('type', 'output'),
                            'node_id': node_id,
                        })
                job.status = 'completed'
                job.output_images = json.dumps(images)
                job.completed_at = datetime.utcnow()

            elif status_str == 'error':
                msgs = h.get('status', {}).get('messages', [])
                job.status = 'failed'
                job.error_message = str(msgs)
                job.completed_at = datetime.utcnow()

            db.session.commit()

    except Exception:
        # Don't surface transient ComfyUI connectivity errors during polling
        pass

    return jsonify(job.to_dict())


# ── Image proxy ──────────────────────────────────────────────

@comfy_api_bp.route('/jobs/<int:jid>/image')
def api_proxy_image(jid):
    ComfyJob.query.get_or_404(jid)   # verify job exists
    filename = request.args.get('filename', '')
    subfolder = request.args.get('subfolder', '')
    folder_type = request.args.get('type', 'output')

    if not filename:
        return jsonify({'error': '缺少 filename 參數'}), 400

    try:
        content, content_type = comfy_api_service.get_image_bytes(filename, subfolder, folder_type)
        return send_file(io.BytesIO(content), mimetype=content_type)
    except Exception as e:
        return jsonify({'error': str(e)}), 502


# ── Helpers ──────────────────────────────────────────────────

def _validate_and_stringify(wj) -> str | None:
    """Accept str or dict; return JSON string or None if invalid."""
    try:
        if isinstance(wj, str):
            json.loads(wj)          # validate
            return wj
        return json.dumps(wj, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return None


# Keys whose values must become bare JSON integers / floats (not quoted strings).
_INT_PLACEHOLDERS   = {'seed', 'steps', 'width', 'height'}
_FLOAT_PLACEHOLDERS = {'cfg', 'denoise'}


def _apply_placeholders(wf_str: str, placeholders: dict) -> str:
    for key, value in placeholders.items():
        if value == '' or value is None:
            continue

        token = f'%{key}%'

        if key in _INT_PLACEHOLDERS:
            try:
                num = int(value)
            except (ValueError, TypeError):
                num = 0
            wf_str = wf_str.replace(f'"{token}"', str(num))
        elif key in _FLOAT_PLACEHOLDERS:
            try:
                num = float(value)
            except (ValueError, TypeError):
                num = 0.0
            wf_str = wf_str.replace(f'"{token}"', str(num))
        else:
            safe = (str(value)
                    .replace('\\', '\\\\')
                    .replace('"', '\\"')
                    .replace('\n', '\\n')
                    .replace('\r', '\\r')
                    .replace('\t', '\\t'))
            wf_str = wf_str.replace(token, safe)

    return wf_str
