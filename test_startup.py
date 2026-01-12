#!/usr/bin/env python3
"""测试应用启动"""
import sys
import os
sys.path.insert(0, '/app')

try:
    from main import app
    print("✅ 应用导入成功")
    
    # 检查路由
    routes = [route.path for route in app.routes]
    print(f"✅ 路由数量: {len(routes)}")
    print(f"✅ 健康检查路由: {'/api/health' in routes}")
    
    # 检查静态文件目录
    from pathlib import Path
    static_dir = Path('/app/static')
    print(f"✅ 静态文件目录存在: {static_dir.exists()}")
    if static_dir.exists():
        files = list(static_dir.iterdir())
        print(f"✅ 静态文件数量: {len(files)}")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
