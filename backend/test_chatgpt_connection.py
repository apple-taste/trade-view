#!/usr/bin/env python3
"""
ChatGPT-5连接测试脚本

直接测试ChatGPT-5 API连接，无需启动完整后端服务。
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_chatgpt_connection():
    """测试ChatGPT-5 API连接"""
    print("=" * 80)
    print("🧪 ChatGPT-5 连接测试")
    print("=" * 80)
    
    # 检查Token配置
    api_key = os.getenv("AI_BUILDER_TOKEN", "")
    if not api_key:
        print("❌ 错误: AI_BUILDER_TOKEN未配置")
        print("💡 提示: 请在.env文件中设置AI_BUILDER_TOKEN")
        return False
    
    print(f"✅ Token已配置: {api_key[:20]}...")
    
    # API配置
    base_url = "https://space.ai-builders.com/backend"
    chat_url = f"{base_url}/v1/chat/completions"
    model = "gpt-5"
    test_message = "你好，请用一句话介绍你自己。"
    
    print(f"🌐 API端点: {chat_url}")
    print(f"🤖 模型: {model}")
    print(f"📝 测试消息: {test_message}")
    print()
    
    # 准备请求
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是一个友好的AI助手。"
            },
            {
                "role": "user",
                "content": test_message
            }
        ],
        "temperature": 1.0,
        "max_tokens": 500  # 增加到500，避免输出限制
    }
    
    print("📤 发送请求...")
    print(f"📤 请求URL: {chat_url}")
    print(f"📤 请求头: Authorization: Bearer {api_key[:20]}...")
    print(f"📤 请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print()
    
    # SSL配置
    disable_ssl_verify = os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true"
    if disable_ssl_verify:
        print("⚠️  SSL证书验证已禁用（仅用于开发环境）")
        verify_ssl = False
    else:
        verify_ssl = True
    
    start_time = time.time()
    
    try:
        response = requests.post(
            chat_url,
            json=payload,
            headers=headers,
            timeout=30,
            verify=verify_ssl
        )
        
        response_time = time.time() - start_time
        
        print(f"📥 响应状态码: {response.status_code}")
        print(f"⏱️ 响应时间: {response_time:.2f}秒")
        print()
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = result.get("usage", {})
            
            print("=" * 80)
            print("✅ ChatGPT-5连接成功！")
            print("=" * 80)
            print(f"📝 AI回复: {ai_response}")
            print()
            print(f"📊 Token使用统计:")
            print(f"   • 提示Token: {usage.get('prompt_tokens', 0)}")
            print(f"   • 完成Token: {usage.get('completion_tokens', 0)}")
            print(f"   • 总Token: {usage.get('total_tokens', 0)}")
            print("=" * 80)
            return True
        else:
            error_text = response.text
            print("=" * 80)
            print(f"❌ API请求失败: HTTP {response.status_code}")
            print("=" * 80)
            print(f"错误详情: {error_text[:500]}")
            print("=" * 80)
            return False
            
    except requests.exceptions.Timeout:
        print("=" * 80)
        print("❌ 请求超时")
        print("=" * 80)
        return False
    except requests.exceptions.ConnectionError as e:
        print("=" * 80)
        print("❌ 网络连接错误")
        print("=" * 80)
        print(f"错误详情: {str(e)}")
        print("=" * 80)
        return False
    except Exception as e:
        print("=" * 80)
        print(f"❌ 未知错误: {type(e).__name__}")
        print("=" * 80)
        print(f"错误详情: {str(e)}")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = test_chatgpt_connection()
    sys.exit(0 if success else 1)
