#!/usr/bin/env python3
import requests
import json
import time
import uuid

# 服务器地址
BASE_URL = "http://localhost:8000"

def test_a_plus_b_problem():
    """测试A+B Problem的完整评测流程"""
    print("开始测试A+B Problem评测...")
    
    # 1. 创建管理员会话
    print("1. 创建管理员会话...")
    admin_data = {"username": "admin", "password": "admintestpassword"}
    response = requests.post(f"{BASE_URL}/api/auth/login", json=admin_data)
    if response.status_code != 200:
        print(f"管理员登录失败: {response.status_code}")
        return False
    
    admin_cookies = response.cookies
    print("管理员登录成功")
    
    # 2. 创建A+B Problem
    print("2. 创建A+B Problem...")
    problem_id = f"a_plus_b_{uuid.uuid4().hex[:8]}"
    problem_data = {
        "id": problem_id,
        "title": "A+B Problem",
        "description": "计算两个整数的和",
        "input_description": "输入两个整数a和b，用空格分隔",
        "output_description": "输出a+b的结果",
        "samples": [
            {"input": "1 2\n", "output": "3\n"},
            {"input": "5 7\n", "output": "12\n"}
        ],
        "testcases": [
            {"input": "1 2\n", "output": "3\n"},
            {"input": "5 7\n", "output": "12\n"},
            {"input": "0 0\n", "output": "0\n"},
            {"input": "-1 1\n", "output": "0\n"},
            {"input": "1000000000 1000000000\n", "output": "2000000000\n"}
        ],
        "constraints": "|a|,|b| <= 10^9",
        "time_limit": 1.0,
        "memory_limit": 128
    }
    
    response = requests.post(f"{BASE_URL}/api/problems/", json=problem_data, cookies=admin_cookies)
    if response.status_code != 200:
        print(f"创建题目失败: {response.status_code}")
        print(response.text)
        return False
    
    print(f"题目创建成功: {problem_id}")
    
    # 3. 创建测试用户
    print("3. 创建测试用户...")
    user = f"test_user_{uuid.uuid4().hex[:8]}"
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
    
    # 5. 提交正确的解决方案
    print("5. 提交正确的解决方案...")
    correct_code = "a, b = map(int, input().split())\nprint(a + b)"
    submission_data = {
        "problem_id": problem_id,
        "language": "python",
        "code": correct_code
    }
    
    response = requests.post(f"{BASE_URL}/api/submissions/", json=submission_data, cookies=user_cookies)
    if response.status_code != 200:
        print(f"提交解决方案失败: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    submission_id = data["data"]["submission_id"]
    print(f"提交成功，提交ID: {submission_id}")
    
    # 6. 等待评测完成
    print("6. 等待评测完成...")
    time.sleep(2)
    
    # 7. 获取评测结果
    print("7. 获取评测结果...")
    response = requests.get(f"{BASE_URL}/api/submissions/{submission_id}", cookies=user_cookies)
    if response.status_code != 200:
        print(f"获取评测结果失败: {response.status_code}")
        return False
    
    result_data = response.json()
    print(f"评测结果: {json.dumps(result_data, indent=2, ensure_ascii=False)}")
    
    # 8. 提交错误的解决方案
    print("8. 提交错误的解决方案...")
    wrong_code = "a, b = map(int, input().split())\nprint(a - b)"  # 减法而不是加法
    submission_data["code"] = wrong_code
    
    response = requests.post(f"{BASE_URL}/api/submissions/", json=submission_data, cookies=user_cookies)
    if response.status_code != 200:
        print(f"提交错误解决方案失败: {response.status_code}")
        return False
    
    data = response.json()
    wrong_submission_id = data["data"]["submission_id"]
    print(f"错误解决方案提交成功，提交ID: {wrong_submission_id}")
    
    # 9. 等待评测完成
    print("9. 等待错误解决方案评测完成...")
    time.sleep(2)
    
    # 10. 获取错误评测结果
    print("10. 获取错误评测结果...")
    response = requests.get(f"{BASE_URL}/api/submissions/{wrong_submission_id}", cookies=user_cookies)
    if response.status_code != 200:
        print(f"获取错误评测结果失败: {response.status_code}")
        return False
    
    wrong_result_data = response.json()
    print(f"错误评测结果: {json.dumps(wrong_result_data, indent=2, ensure_ascii=False)}")
    
    # 11. 验证结果
    print("11. 验证评测结果...")
    correct_score = result_data["data"]["score"]
    correct_counts = result_data["data"]["counts"]
    wrong_score = wrong_result_data["data"]["score"]
    
    print(f"正确解决方案得分: {correct_score}/{correct_counts}")
    print(f"错误解决方案得分: {wrong_score}/{correct_counts}")
    
    if correct_score == correct_counts and wrong_score < correct_counts:
        print("✅ A+B Problem评测功能正常！")
        return True
    else:
        print("❌ A+B Problem评测功能异常！")
        return False

if __name__ == "__main__":
    try:
        success = test_a_plus_b_problem()
        if success:
            print("\n🎉 测试通过！A+B Problem评测系统工作正常。")
        else:
            print("\n💥 测试失败！A+B Problem评测系统存在问题。")
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 