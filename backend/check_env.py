#!/usr/bin/env python3
"""快速检查环境变量配置"""

import os
from pathlib import Path
from dotenv import load_dotenv

print("=" * 80)
print("🔍 环境变量配置检查")
print("=" * 80)

# 检查.env文件
env_file = Path(__file__).parent / '.env'
print(f"📄 .env文件路径: {env_file}")
print(f"📄 .env文件存在: {'✅ 是' if env_file.exists() else '❌ 否'}")

if env_file.exists():
    print(f"📄 .env文件大小: {env_file.stat().st_size} bytes")
    print()
    print("📄 .env文件内容（隐藏敏感信息）:")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if 'TOKEN' in line or 'PASSWORD' in line:
                    key = line.split('=')[0]
                    value = line.split('=')[1] if '=' in line else ''
                    if value:
                        display_value = f"{value[:20]}..." if len(value) > 20 else "***"
                    else:
                        display_value = "(空)"
                    print(f"   • {key}={display_value}")
                else:
                    print(f"   • {line[:80]}")

print()
print("=" * 80)
print("🔍 加载环境变量...")
load_dotenv(dotenv_path=env_file)

print()
print("=" * 80)
print("📋 环境变量检查:")
print("=" * 80)

ai_token = os.getenv("AI_BUILDER_TOKEN", "")
smtp_server = os.getenv("SMTP_SERVER", "")
smtp_username = os.getenv("SMTP_USERNAME", "")

print(f"✅ AI_BUILDER_TOKEN: {'✅ 已配置' if ai_token else '❌ 未配置'}")
if ai_token:
    print(f"   • Token前缀: {ai_token[:20]}...")
    print(f"   • Token长度: {len(ai_token)}字符")

print(f"✅ SMTP_SERVER: {'✅ 已配置' if smtp_server else '⚠️  未配置'}")
if smtp_server:
    print(f"   • SMTP服务器: {smtp_server}")

print(f"✅ SMTP_USERNAME: {'✅ 已配置' if smtp_username else '⚠️  未配置'}")

print()
print("=" * 80)
if ai_token:
    print("✅ 环境变量配置正常！")
else:
    print("❌ AI_BUILDER_TOKEN未配置！")
    print("💡 请在.env文件中设置AI_BUILDER_TOKEN")
print("=" * 80)
