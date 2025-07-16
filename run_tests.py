#!/usr/bin/env python3
"""
运行pytest测试的启动脚本
在导入任何测试模块之前修复TestClient兼容性问题
"""

# 必须在导入任何其他模块之前执行TestClient修复
import sys
import fastapi.testclient
import starlette.testclient

print("🔧 正在修复TestClient兼容性问题...")

# 保存原始的TestClient
OriginalFastAPITestClient = fastapi.testclient.TestClient
OriginalStarletteTestClient = starlette.testclient.TestClient

class CompatibleTestClient:
    def __init__(self, app, **kwargs):
        try:
            # 尝试使用fastapi的TestClient
            self._client = OriginalFastAPITestClient(app, **kwargs)
        except TypeError as e:
            if "unexpected keyword argument 'app'" in str(e):
                # 如果fastapi的TestClient有问题，尝试starlette的TestClient
                try:
                    self._client = OriginalStarletteTestClient(app, **kwargs)
                except TypeError:
                    # 最后的备选方案：只传app参数
                    self._client = OriginalStarletteTestClient(app)
            else:
                raise e
    
    def __getattr__(self, name):
        return getattr(self._client, name)

# 替换两个模块的TestClient
fastapi.testclient.TestClient = CompatibleTestClient
starlette.testclient.TestClient = CompatibleTestClient

print("✅ TestClient兼容性修复完成")

# 现在运行pytest
if __name__ == "__main__":
    import pytest
    
    print("🚀 开始运行pytest测试...")
    
    # 运行所有测试
    exit_code = pytest.main([
        "tests/",
        "-v",
        "--tb=short"
    ])
    
    if exit_code == 0:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n💥 测试失败，退出码: {exit_code}")
    
    sys.exit(exit_code) 