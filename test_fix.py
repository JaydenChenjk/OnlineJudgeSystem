#!/usr/bin/env python3
"""
TestClient兼容性修复 + 测试脚本
"""

# 必须在导入任何其他模块之前执行TestClient修复
import sys
import fastapi.testclient

# 保存原始的TestClient
OriginalTestClient = fastapi.testclient.TestClient

class CompatibleTestClient:
    def __init__(self, app, **kwargs):
        try:
            # 尝试原始方式
            self._client = OriginalTestClient(app, **kwargs)
        except TypeError as e:
            if "unexpected keyword argument 'app'" in str(e):
                # 新版本方式，使用backend参数
                self._client = OriginalTestClient(app, backend="asyncio", **kwargs)
            else:
                raise e
    
    def __getattr__(self, name):
        return getattr(self._client, name)

# 替换TestClient
fastapi.testclient.TestClient = CompatibleTestClient

import requests
import time
import json
import uuid

BASE_URL = "http://localhost:8000"

def test_submission_fix():
    """测试提交修复"""
    session = requests.Session()
    
    # 生成随机题目ID和用户名
    problem_id = f"test_fix_{uuid.uuid4().hex[:8]}"
    username = f"test_fix_user_{uuid.uuid4().hex[:8]}"
    
    # 1. 管理员登录
    print("1. 管理员登录...")
    login_data = {"username": "admin", "password": "admintestpassword"}
    response = session.post(f"{BASE_URL}/api/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"登录失败: {response.status_code}")
        print(response.text)
        return False
    
    print("管理员登录成功")
    
    # 2. 创建测试题目
    print("2. 创建测试题目...")
    problem_data = {
        "id": problem_id,
        "title": "测试修复题目",
        "description": "计算a+b",
        "input_description": "两个整数",
        "output_description": "它们的和",
        "samples": [{"input": "1 2\n", "output": "3\n"}],
        "testcases": [{"input": "1 2\n", "output": "3\n"}],
        "constraints": "|a|,|b| <= 10^9",
        "time_limit": 1.0,
        "memory_limit": 128
    }
    
    response = session.post(f"{BASE_URL}/api/problems/", json=problem_data)
    if response.status_code != 200:
        print(f"创建题目失败: {response.status_code}")
        print(response.text)
        return False
    
    print("题目创建成功")
    
    # 3. 创建测试用户
    print("3. 创建测试用户...")
    user_data = {"username": username, "password": "testpass"}
    response = session.post(f"{BASE_URL}/api/users/", json=user_data)
    if response.status_code != 200:
        print(f"创建用户失败: {response.status_code}")
        print(response.text)
        return False
    
    print("用户创建成功")
    
    # 4. 用户登录
    print("4. 用户登录...")
    user_login_data = {"username": username, "password": "testpass"}
    response = session.post(f"{BASE_URL}/api/auth/login", json=user_login_data)
    if response.status_code != 200:
        print(f"用户登录失败: {response.status_code}")
        print(response.text)
        return False
    
    print("用户登录成功")
    
    # 5. 提交正确代码
    print("5. 提交正确代码...")
    submission_data = {
        "problem_id": problem_id,
        "language": "python",
        "code": "a, b = map(int, input().split())\nprint(a + b)"
    }
    
    response = session.post(f"{BASE_URL}/api/submissions/", json=submission_data)
    if response.status_code != 200:
        print(f"提交失败: {response.status_code}")
        print(response.text)
        return False
    
    submission_id = response.json()["data"]["submission_id"]
    print(f"提交成功，ID: {submission_id}")
    
    # 6. 等待评测
    print("6. 等待评测...")
    time.sleep(3)
    
    # 7. 获取结果
    print("7. 获取结果...")
    response = session.get(f"{BASE_URL}/api/submissions/{submission_id}")
    if response.status_code != 200:
        print(f"获取结果失败: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    print(f"正确代码评测结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 检查分数
    if result["data"]["score"] == 10:
        print("✅ 正确代码得分正确")
    else:
        print(f"❌ 正确代码得分错误！期望得分10，实际得分{result['data']['score']}")
        return False
    
    # 8. 提交错误代码
    print("8. 提交错误代码...")
    wrong_submission_data = {
        "problem_id": problem_id,
        "language": "python",
        "code": "a, b = map(int, input().split())\nprint(a - b)"  # 错误：减法而不是加法
    }
    
    response = session.post(f"{BASE_URL}/api/submissions/", json=wrong_submission_data)
    if response.status_code != 200:
        print(f"提交失败: {response.status_code}")
        print(response.text)
        return False
    
    wrong_submission_id = response.json()["data"]["submission_id"]
    print(f"错误代码提交成功，ID: {wrong_submission_id}")
    
    # 9. 等待评测
    print("9. 等待评测...")
    time.sleep(3)
    
    # 10. 获取错误代码结果
    print("10. 获取错误代码结果...")
    response = session.get(f"{BASE_URL}/api/submissions/{wrong_submission_id}")
    if response.status_code != 200:
        print(f"获取结果失败: {response.status_code}")
        print(response.text)
        return False
    
    wrong_result = response.json()
    print(f"错误代码评测结果: {json.dumps(wrong_result, indent=2, ensure_ascii=False)}")
    
    # 检查错误代码分数
    if wrong_result["data"]["score"] == 0:
        print("✅ 错误代码得分正确")
        return True
    else:
        print(f"❌ 错误代码得分错误！期望得分0，实际得分{wrong_result['data']['score']}")
        return False

def run_pytest_with_fix():
    """运行pytest并应用TestClient修复"""
    import subprocess
    import os
    
    # 设置环境变量，让pytest在导入时先执行我们的修复
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd() + ':' + env.get('PYTHONPATH', '')
    
    # 运行pytest
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 'tests/', '-v'
    ], env=env)
    
    return result.returncode == 0

if __name__ == "__main__":
    print("选择运行模式:")
    print("1. 测试业务功能")
    print("2. 运行pytest测试")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        success = test_submission_fix()
        if success:
            print("\n🎉 业务功能测试成功！")
        else:
            print("\n💥 业务功能测试失败！")
    elif choice == "2":
        print("运行pytest测试...")
        success = run_pytest_with_fix()
        if success:
            print("\n🎉 pytest测试通过！")
        else:
            print("\n💥 pytest测试失败！")
    else:
        print("无效选择") 