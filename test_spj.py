#!/usr/bin/env python3
import requests
import json
import time
import uuid

# 服务器地址
BASE_URL = "http://localhost:8000"

def test_spj_functionality():
    """测试SPJ功能的完整流程"""
    print("开始测试SPJ功能...")
    
    # 1. 管理员登录
    print("1. 管理员登录...")
    admin_data = {"username": "admin", "password": "admintestpassword"}
    response = requests.post(f"{BASE_URL}/api/auth/login", json=admin_data)
    if response.status_code != 200:
        print(f"管理员登录失败: {response.status_code}")
        return False
    
    admin_cookies = response.cookies
    print("管理员登录成功")
    
    # 2. 创建SPJ题目
    print("2. 创建SPJ题目...")
    problem_id = f"spj_test_{uuid.uuid4().hex[:8]}"
    problem_data = {
        "id": problem_id,
        "title": "SPJ测试题目",
        "description": "输出任意一组满足条件的解",
        "input_description": "输入一个整数n",
        "output_description": "输出两个整数a和b，使得a+b=n",
        "samples": [
            {"input": "5\n", "output": "2 3\n"}
        ],
        "testcases": [
            {"input": "5\n", "output": "2 3\n"},
            {"input": "10\n", "output": "3 7\n"},
            {"input": "0\n", "output": "0 0\n"}
        ],
        "constraints": "1 <= n <= 100",
        "time_limit": 1.0,
        "memory_limit": 128,
        "judge_mode": "spj"  # 使用SPJ模式
    }
    
    response = requests.post(f"{BASE_URL}/api/problems/", json=problem_data, cookies=admin_cookies)
    if response.status_code != 200:
        print(f"创建题目失败: {response.status_code}")
        print(response.text)
        return False
    
    print(f"题目创建成功: {problem_id}")
    
    # 3. 上传SPJ脚本
    print("3. 上传SPJ脚本...")
    spj_script = '''#!/usr/bin/env python3
import json
import sys

def judge(input_data, expected_output, actual_output):
    """SPJ脚本：检查输出是否满足条件"""
    try:
        # 解析输入
        n = int(input_data.strip())
        
        # 解析用户输出
        lines = actual_output.strip().split('\\n')
        if len(lines) == 0:
            return {"status": "WA", "message": "输出为空"}
        
        parts = lines[0].strip().split()
        if len(parts) != 2:
            return {"status": "WA", "message": "输出格式错误，需要两个整数"}
        
        try:
            a, b = int(parts[0]), int(parts[1])
        except ValueError:
            return {"status": "WA", "message": "输出不是整数"}
        
        # 检查条件：a + b = n
        if a + b == n:
            return {"status": "AC", "message": "答案正确"}
        else:
            return {"status": "WA", "message": f"答案错误：{a} + {b} != {n}"}
    
    except Exception as e:
        return {"status": "SPJ_ERROR", "message": f"SPJ脚本执行错误: {str(e)}"}

if __name__ == "__main__":
    # 从标准输入读取数据
    input_json = sys.stdin.read()
    data = json.loads(input_json)
    
    # 执行评测
    result = judge(data["input"], data["expected_output"], data["actual_output"])
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False))
'''
    
    # 上传SPJ脚本
    files = {"file": ("spj_script.py", spj_script.encode('utf-8'), "text/plain")}
    response = requests.post(f"{BASE_URL}/api/spj/upload/{problem_id}", files=files, cookies=admin_cookies)
    if response.status_code != 200:
        print(f"上传SPJ脚本失败: {response.status_code}")
        print(response.text)
        return False
    
    print("SPJ脚本上传成功")
    
    # 4. 测试SPJ脚本
    print("4. 测试SPJ脚本...")
    test_data = {
        "input_data": "5",
        "expected_output": "2 3",
        "actual_output": "2 3"
    }
    response = requests.post(f"{BASE_URL}/api/spj/test/{problem_id}", data=test_data, cookies=admin_cookies)
    if response.status_code != 200:
        print(f"测试SPJ脚本失败: {response.status_code}")
        print(response.text)
        return False
    
    test_result = response.json()
    print(f"SPJ测试结果: {json.dumps(test_result, indent=2, ensure_ascii=False)}")
    
    # 5. 创建测试用户
    print("5. 创建测试用户...")
    user = f"spj_user_{uuid.uuid4().hex[:8]}"
    user_data = {"username": user, "password": "test123"}
    response = requests.post(f"{BASE_URL}/api/users/", json=user_data, cookies=admin_cookies)
    if response.status_code != 200:
        print(f"创建用户失败: {response.status_code}")
        return False
    
    print(f"用户创建成功: {user}")
    
    # 6. 用户登录
    print("6. 用户登录...")
    response = requests.post(f"{BASE_URL}/api/auth/login", json=user_data)
    if response.status_code != 200:
        print(f"用户登录失败: {response.status_code}")
        return False
    
    user_cookies = response.cookies
    print("用户登录成功")
    
    # 7. 提交正确的解决方案
    print("7. 提交正确的解决方案...")
    correct_code = "n = int(input())\nprint(f\"{n} 0\")"  # 输出 n 0，满足条件
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
    
    # 8. 等待评测完成
    print("8. 等待评测完成...")
    time.sleep(3)
    
    # 9. 获取评测结果
    print("9. 获取评测结果...")
    response = requests.get(f"{BASE_URL}/api/submissions/{submission_id}", cookies=user_cookies)
    if response.status_code != 200:
        print(f"获取评测结果失败: {response.status_code}")
        return False
    
    result_data = response.json()
    print(f"正确解决方案评测结果: {json.dumps(result_data, indent=2, ensure_ascii=False)}")
    
    # 10. 提交错误的解决方案
    print("10. 提交错误的解决方案...")
    wrong_code = "n = int(input())\nprint(f\"{n+1} 0\")"  # 输出 n+1 0，不满足条件
    submission_data["code"] = wrong_code
    
    response = requests.post(f"{BASE_URL}/api/submissions/", json=submission_data, cookies=user_cookies)
    if response.status_code != 200:
        print(f"提交错误解决方案失败: {response.status_code}")
        return False
    
    data = response.json()
    wrong_submission_id = data["data"]["submission_id"]
    print(f"错误解决方案提交成功，提交ID: {wrong_submission_id}")
    
    # 11. 等待评测完成
    print("11. 等待错误解决方案评测完成...")
    time.sleep(3)
    
    # 12. 获取错误评测结果
    print("12. 获取错误评测结果...")
    response = requests.get(f"{BASE_URL}/api/submissions/{wrong_submission_id}", cookies=user_cookies)
    if response.status_code != 200:
        print(f"获取错误评测结果失败: {response.status_code}")
        return False
    
    wrong_result_data = response.json()
    print(f"错误解决方案评测结果: {json.dumps(wrong_result_data, indent=2, ensure_ascii=False)}")
    
    # 13. 验证结果
    print("13. 验证SPJ评测结果...")
    correct_score = result_data["data"]["score"]
    correct_counts = result_data["data"]["counts"]
    wrong_score = wrong_result_data["data"]["score"]
    
    print(f"正确解决方案得分: {correct_score}/{correct_counts}")
    print(f"错误解决方案得分: {wrong_score}/{correct_counts}")
    
    if correct_score == correct_counts and wrong_score < correct_counts:
        print("✅ SPJ功能测试通过！")
        return True
    else:
        print("❌ SPJ功能测试失败！")
        return False

if __name__ == "__main__":
    try:
        success = test_spj_functionality()
        if success:
            print("\n🎉 SPJ功能测试通过！Special Judge系统工作正常。")
        else:
            print("\n💥 SPJ功能测试失败！Special Judge系统存在问题。")
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 