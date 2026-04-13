# -*- coding: utf-8 -*-
"""Wildcard 管理系統 - 入口點"""

from webapp import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
