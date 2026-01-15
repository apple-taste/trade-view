#!/usr/bin/env python3
"""
PostgreSQL数据库设置助手
帮助用户快速配置PostgreSQL数据库连接
"""

import json
import sys
import os

def main():
    print("=" * 80)
    print("🚀 PostgreSQL数据库设置助手")
    print("=" * 80)
    print()
    print("📋 请按照以下步骤操作：")
    print()
    print("1. 访问 https://supabase.com/ 创建账号和项目")
    print("2. 在 Settings → Database → Connection string → URI 获取连接字符串")
    print("3. 将 [YOUR-PASSWORD] 替换为你的实际密码")
    print()
    print("连接字符串格式：")
    print("  postgresql://postgres:密码@db.xxxxx.supabase.co:5432/postgres")
    print()
    
    # 读取现有配置
    config_path = 'deploy-config.json'
    if not os.path.exists(config_path):
        print(f"❌ 错误：找不到 {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # 显示当前配置
    current_db_url = config.get('env_vars', {}).get('DATABASE_URL', '未设置')
    if current_db_url != '未设置':
        # 隐藏密码
        display_url = current_db_url.split('@')[0] + '@***'
        print(f"当前DATABASE_URL: {display_url}")
        print()
        overwrite = input("是否要更新？(y/n): ").strip().lower()
        if overwrite != 'y':
            print("已取消")
            return
        print()
    
    # 获取用户输入
    print("请粘贴你的PostgreSQL连接字符串：")
    print("（可以直接粘贴，脚本会自动处理）")
    print()
    database_url = input("DATABASE_URL: ").strip()
    
    if not database_url:
        print("❌ 错误：连接字符串不能为空")
        sys.exit(1)
    
    # 验证格式
    if not database_url.startswith('postgresql://'):
        print("⚠️  警告：连接字符串格式可能不正确（应该以 postgresql:// 开头）")
        confirm = input("是否继续？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
    
    # 确保env_vars存在
    if 'env_vars' not in config:
        config['env_vars'] = {}
    
    # 更新DATABASE_URL
    config['env_vars']['DATABASE_URL'] = database_url
    
    # 保留其他必要的环境变量
    if 'JWT_SECRET' not in config['env_vars']:
        config['env_vars']['JWT_SECRET'] = 'your_jwt_secret_here'
    if 'NODE_ENV' not in config['env_vars']:
        config['env_vars']['NODE_ENV'] = 'production'
    if 'LOG_LEVEL' not in config['env_vars']:
        config['env_vars']['LOG_LEVEL'] = 'info'
    
    # 保存配置
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # 隐藏密码显示
        display_url = database_url.split('@')[0] + '@***'
        print()
        print("=" * 80)
        print("✅ 配置已更新！")
        print("=" * 80)
        print()
        print(f"📝 DATABASE_URL: {display_url}")
        print()
        print("📋 下一步：")
        print()
        print("1. 确保本地 .env 已包含 DATABASE_URL 与 JWT_SECRET")
        print("2. 触发部署：")
        print("   ./deploy.sh")
        print()
        
        print()
        print("✅ 配置已保存到 deploy-config.json")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
