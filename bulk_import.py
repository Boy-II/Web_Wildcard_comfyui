# -*- coding: utf-8 -*-
"""
批量匯入腳本 - 從 E:\Wildcard 匯入所有資料
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='批量匯入 Wildcard 資料')
    parser.add_argument('directory', nargs='?', default='E:\\Wildcard',
                       help='要匯入的目錄路徑 (預設: E:\\Wildcard)')
    parser.add_argument('--translate', '-t', action='store_true',
                       help='使用 Ollama 翻譯內容')
    parser.add_argument('--ai-classify', '-c', action='store_true',
                       help='使用 Ollama AI 協助分類')
    parser.add_argument('--no-recursive', action='store_true',
                       help='不遞迴搜尋子目錄')
    parser.add_argument('--test', action='store_true',
                       help='測試模式：只顯示會匯入哪些檔案，不實際匯入')

    args = parser.parse_args()

    directory = Path(args.directory)

    if not directory.exists():
        print(f"❌ 錯誤：目錄不存在: {directory}")
        return 1

    print("=" * 70)
    print("Wildcard 批量匯入工具")
    print("=" * 70)
    print(f"目錄: {directory}")
    print(f"遞迴搜尋: {'否' if args.no_recursive else '是'}")
    print(f"AI 翻譯: {'是' if args.translate else '否'}")
    print(f"AI 分類: {'是' if args.ai_classify else '否'}")
    print(f"測試模式: {'是' if args.test else '否'}")
    print("=" * 70)

    # 統計檔案
    if args.no_recursive:
        txt_files = list(directory.glob('*.txt'))
    else:
        txt_files = list(directory.rglob('*.txt'))

    print(f"\n找到 {len(txt_files)} 個 TXT 檔案")

    if args.test:
        print("\n【測試模式】會匯入以下檔案：")
        for i, f in enumerate(txt_files[:20], 1):
            print(f"  {i}. {f.relative_to(directory)}")
        if len(txt_files) > 20:
            print(f"  ... 還有 {len(txt_files) - 20} 個檔案")
        return 0

    # 確認
    print("\n即將開始匯入...")
    if args.translate or args.ai_classify:
        print("⚠️  警告：使用 AI 功能會大幅增加處理時間！")

    response = input("\n確定要繼續嗎？(yes/no): ")
    if response.lower() != 'yes':
        print("已取消")
        return 0

    # 開始匯入
    print("\n開始匯入...")
    print("-" * 70)

    try:
        from app import app
        from app import import_from_directory

        with app.app_context():
            # 檢查 Ollama 連接
            if args.translate or args.ai_classify:
                try:
                    from ollama_helper import OllamaHelper
                    ollama = OllamaHelper()
                    if ollama.check_connection():
                        print("✓ Ollama 服務連接成功")
                        print(f"  使用模型: {ollama.model}")
                    else:
                        print("✗ 無法連接到 Ollama 服務")
                        print("  請確保 Ollama 已啟動並運行 qwen2.5:7b 模型")
                        response = input("繼續但不使用 AI 功能嗎？(yes/no): ")
                        if response.lower() != 'yes':
                            return 1
                        args.translate = False
                        args.ai_classify = False
                except ImportError:
                    print("✗ ollama_helper 模組載入失敗")
                    return 1

            imported, skipped, errors = import_from_directory(
                str(directory),
                use_ollama_classify=args.ai_classify,
                use_ollama_translate=args.translate,
                recursive=not args.no_recursive
            )

            print("-" * 70)
            print("\n✓ 匯入完成！")
            print(f"  已匯入: {imported} 條")
            print(f"  已跳過: {skipped} 條（重複）")
            print(f"  錯誤: {len(errors)} 個")

            if errors:
                print("\n錯誤列表：")
                for error in errors[:10]:
                    print(f"  - {error}")
                if len(errors) > 10:
                    print(f"  ... 還有 {len(errors) - 10} 個錯誤")

            return 0

    except Exception as e:
        print(f"\n❌ 匯入失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
