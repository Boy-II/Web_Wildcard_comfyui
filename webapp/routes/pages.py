# -*- coding: utf-8 -*-
from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    return render_template('index.html')


@pages_bp.route('/wildcards')
def wildcards_page():
    return render_template('wildcards.html')


@pages_bp.route('/import')
def import_page():
    return render_template('import.html')


@pages_bp.route('/export')
def export_page():
    return render_template('export.html')


@pages_bp.route('/comfy-monitor')
def comfy_monitor_page():
    return render_template('comfy_monitor.html')


@pages_bp.route('/translation-settings')
def translation_settings_page():
    return render_template('translation_settings.html')


@pages_bp.route('/prompt-builder')
def prompt_builder_page():
    return render_template('prompt_builder.html')
