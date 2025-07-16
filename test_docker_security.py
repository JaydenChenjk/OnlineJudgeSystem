#!/usr/bin/env python3
import requests
import json
import time
import uuid

# 服务器地址
BASE_URL = "http://localhost:8000"

def test_docker_security():
    """测试Docker安全机制"""
    print("开始测试Docker安全机制...")
    
    # 1. 管理员登录
    print("1. 管理员登录...")
    admin_data = {"username": "admin", "password": "admintestpassword"}
    response = requests.post(f"{BASE_URL}/api/auth/login", json=admin_data)
    if response.status_code != 200:
        print(f"管理员登录失败: {response.status_code}")
        return False
    
    admin_cookies = response.cookies
    print("管理员登录成功")
    
    # 2. 创建测试题目
    print("2. 创建测试题目...")
    problem_id = f"docker_test_{uuid.uuid4().hex[:8]}"
    problem_data = {
        "id": problem_id,
        "title": "Docker安全测试",
        "description": "测试Docker安全机制",
        "input_description": "输入一个整数n",
        "output_description": "输出n的平方",
        "samples": [
            {"input": "5\n", "output": "25\n"}
        ],
        "testcases": [
            {"input": "5\n", "output": "25\n"},
            {"input": "10\n", "output": "100\n"}
        ],
        "constraints": "1 <= n <= 100",
        "time_limit": 2.0,
        "memory_limit": 64
    }
    
    response = requests.post(f"{BASE_URL}/api/problems/", json=problem_data, cookies=admin_cookies)
    if response.status_code != 200:
        print(f"创建题目失败: {response.status_code}")
        print(response.text)
        return False
    
    print(f"题目创建成功: {problem_id}")
    
    # 3. 创建测试用户
    print("3. 创建测试用户...")
    user = f"docker_user_{uuid.uuid4().hex[:8]}"
    user_data = {"username": user, "password": "test123"}
    response = requests.post(f"{BASE_URL}/api/users/", json=user_data, cookies=admin_cookies)
    if response.status_code != 200:
        print(f"创建用户失败: {response.status_code}")
        return False
    
    print(f"用户创建成功: {user}")
    
    # 4. 用户登录
    print("4. 用户登录...")
    response = requests.post(f"{BASE_URL}/api/auth/login", json=user_data)
    if response.status_code != 200:
        print(f"用户登录失败: {response.status_code}")
        return False
    
    user_cookies = response.cookies
    print("用户登录成功")
    
    # 5. 测试正常Python代码
    print("5. 测试正常Python代码...")
    normal_python_code = "n = int(input())\nprint(n * n)"
    submission_data = {
        "problem_id": problem_id,
        "language": "python",
        "code": normal_python_code
    }
    
    response = requests.post(f"{BASE_URL}/api/submissions/", json=submission_data, cookies=user_cookies)
    if response.status_code != 200:
        print(f"提交正常代码失败: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    normal_submission_id = data["data"]["submission_id"]
    print(f"正常代码提交成功，提交ID: {normal_submission_id}")
    
    # 6. 等待评测完成
    print("6. 等待正常代码评测完成...")
    time.sleep(5)
    
    # 7. 获取正常代码评测结果
    print("7. 获取正常代码评测结果...")
    response = requests.get(f"{BASE_URL}/api/submissions/{normal_submission_id}", cookies=user_cookies)
    if response.status_code != 200:
        print(f"获取正常代码评测结果失败: {response.status_code}")
        return False
    
    normal_result = response.json()
    print(f"正常代码评测结果: {json.dumps(normal_result, indent=2, ensure_ascii=False)}")
    
    # 8. 测试恶意Python代码（尝试系统调用）
    print("8. 测试恶意Python代码...")
    malicious_python_code = '''
import os
import subprocess
print("尝试执行系统命令...")
os.system("ls /")
subprocess.call(["echo", "恶意代码"])
print("25")
'''
    
    submission_data["code"] = malicious_python_code
    response = requests.post(f"{BASE_URL}/api/submissions/", json=submission_data, cookies=user_cookies)
    if response.status_code != 200:
        print(f"提交恶意代码失败: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    malicious_submission_id = data["data"]["submission_id"]
    print(f"恶意代码提交成功，提交ID: {malicious_submission_id}")
    
    # 9. 等待评测完成
    print("9. 等待恶意代码评测完成...")
    time.sleep(5)
    
    # 10. 获取恶意代码评测结果
    print("10. 获取恶意代码评测结果...")
    response = requests.get(f"{BASE_URL}/api/submissions/{malicious_submission_id}", cookies=user_cookies)
    if response.status_code != 200:
        print(f"获取恶意代码评测结果失败: {response.status_code}")
        return False
    
    malicious_result = response.json()
    print(f"恶意代码评测结果: {json.dumps(malicious_result, indent=2, ensure_ascii=False)}")
    
    # 11. 测试C++代码
    print("11. 测试C++代码...")
    cpp_code = '''
#include <iostream>
using namespace std;
int main() {
    int n;
    cin >> n;
    cout << n * n << endl;
    return 0;
}
'''
    
    submission_data["code"] = cpp_code
    submission_data["language"] = "cpp"
    response = requests.post(f"{BASE_URL}/api/submissions/", json=submission_data, cookies=user_cookies)
    if response.status_code != 200:
        print(f"提交C++代码失败: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    cpp_submission_id = data["data"]["submission_id"]
    print(f"C++代码提交成功，提交ID: {cpp_submission_id}")
    
    # 12. 等待C++评测完成
    print("12. 等待C++代码评测完成...")
    time.sleep(8)  # C++编译需要更多时间
    
    # 13. 获取C++评测结果
    print("13. 获取C++代码评测结果...")
    response = requests.get(f"{BASE_URL}/api/submissions/{cpp_submission_id}", cookies=user_cookies)
    if response.status_code != 200:
        print(f"获取C++代码评测结果失败: {response.status_code}")
        return False
    
    cpp_result = response.json()
    print(f"C++代码评测结果: {json.dumps(cpp_result, indent=2, ensure_ascii=False)}")
    
    # 14. 测试内存超限
    print("14. 测试内存超限...")
    memory_hog_code = '''
n = int(input())
# 尝试分配大量内存
data = [0] * (n * 1000000)  # 分配大量内存
print(n * n)
'''
    
    submission_data["code"] = memory_hog_code
    submission_data["language"] = "python"
    response = requests.post(f"{BASE_URL}/api/submissions/", json=submission_data, cookies=user_cookies)
    if response.status_code != 200:
        print(f"提交内存超限代码失败: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    memory_submission_id = data["data"]["submission_id"]
    print(f"内存超限代码提交成功，提交ID: {memory_submission_id}")
    
    # 15. 等待内存超限评测完成
    print("15. 等待内存超限代码评测完成...")
    time.sleep(5)
    
    # 16. 获取内存超限评测结果
    print("16. 获取内存超限代码评测结果...")
    response = requests.get(f"{BASE_URL}/api/submissions/{memory_submission_id}", cookies=user_cookies)
    if response.status_code != 200:
        print(f"获取内存超限代码评测结果失败: {response.status_code}")
        return False
    
    memory_result = response.json()
    print(f"内存超限代码评测结果: {json.dumps(memory_result, indent=2, ensure_ascii=False)}")
    
    # 17. 验证结果
    print("17. 验证Docker安全机制...")
    
    # 检查正常代码应该通过
    normal_score = normal_result["data"]["score"]
    normal_counts = normal_result["data"]["counts"]
    
    # 检查恶意代码应该被阻止或失败
    malicious_score = malicious_result["data"]["score"]
    
    # 检查C++代码应该通过
    cpp_score = cpp_result["data"]["score"]
    
    # 检查内存超限应该被检测
    memory_score = memory_result["data"]["score"]
    
    print(f"正常代码得分: {normal_score}/{normal_counts}")
    print(f"恶意代码得分: {malicious_score}/{normal_counts}")
    print(f"C++代码得分: {cpp_score}/{normal_counts}")
    print(f"内存超限代码得分: {memory_score}/{normal_counts}")
    
    # 验证安全机制
    security_ok = True
    
    if normal_score != normal_counts:
        print("❌ 正常代码应该通过")
        security_ok = False
    
    if malicious_score >= normal_counts:
        print("❌ 恶意代码应该被阻止")
        security_ok = False
    
    if cpp_score != normal_counts:
        print("❌ C++代码应该通过")
        security_ok = False
    
    if memory_score >= normal_counts:
        print("❌ 内存超限应该被检测")
        security_ok = False
    
    if security_ok:
        print("✅ Docker安全机制测试通过！")
        return True
    else:
        print("❌ Docker安全机制测试失败！")
        return False

if __name__ == "__main__":
    try:
        success = test_docker_security()
        if success:
            print("\n🎉 Docker安全机制测试通过！系统安全隔离工作正常。")
        else:
            print("\n💥 Docker安全机制测试失败！系统安全隔离存在问题。")
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 