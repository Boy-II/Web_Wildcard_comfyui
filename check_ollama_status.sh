#!/bin/bash
echo "检查 Ollama 模型下载状态..."
echo ""
echo "=== 模型列表 ==="
docker exec wildcard_ollama ollama list

echo ""
echo "=== 下载的 Blob 大小 ==="
docker exec wildcard_ollama sh -c "du -sh /root/.ollama/blobs 2>/dev/null"

echo ""
echo "=== 测试翻译功能 ==="
docker exec wildcard_web python -c "
from ollama_helper import OllamaHelper
h = OllamaHelper(base_url='http://ollama:11434', model='qwen3:8b')
print('连接状态:', h.check_connection())
print('可用模型:', h.list_models())
try:
    result = h.translate_to_chinese('beautiful girl')
    print('翻译测试:', result if result else '翻译失败')
except Exception as e:
    print('翻译错误:', str(e))
"
