#!/usr/bin/env python3
"""
SPJ功能集成测试
测试SPJ功能的完整流程，包括管理界面、权限控制、脚本执行等
"""

import pytest
import requests
import json
import uuid
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class TestSPJIntegration:
    """SPJ功能集成测试类"""
    
    @pytest.fixture
    def admin_session(self):
        """管理员会话"""
        session = requests.Session()
        login_data = {"username": "admin", "password": "admin123"}
        response = session.post(f"{BASE_URL}/api/auth/login", json=login_data)
        assert response.status_code == 200, "管理员登录失败"
        return session
    
    @pytest.fixture
    def user_session(self):
        """普通用户会话"""
        session = requests.Session()
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # 创建用户
        user_data = {"username": username, "password": "testpass"}
        response = session.post(f"{BASE_URL}/api/users/", json=user_data)
        assert response.status_code == 200, "用户创建失败"
        
        # 用户登录
        response = session.post(f"{BASE_URL}/api/auth/login", json=user_data)
        assert response.status_code == 200, "用户登录失败"
        return session
    
    @pytest.fixture
    def spj_problem_id(self):
        """SPJ测试题目ID"""
        return f"spj_test_{uuid.uuid4().hex[:8]}"
    
    @pytest.fixture
    def python_spj_script(self):
        """Python SPJ脚本"""
        return '''#!/usr/bin/env python3
import json
import sys

def main():
    data = json.loads(sys.stdin.read())
    input_data = data["input"]
    expected_output = data["expected_output"]
    actual_output = data["actual_output"]
    
    # 检查输出是否包含期望的内容
    if expected_output.strip() in actual_output.strip():
        result = {"status": "ACCEPTED", "score": 100, "message": "输出正确"}
    else:
        result = {"status": "WRONG_ANSWER", "score": 0, "message": "输出错误"}
    
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''
    
    @pytest.fixture
    def cpp_spj_script(self):
        """C++ SPJ脚本"""
        return '''#include <iostream>
#include <string>
#include <sstream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    string input, expected_output, actual_output;
    
    getline(cin, input);
    getline(cin, expected_output);
    getline(cin, actual_output);
    
    try {
        istringstream iss(input);
        vector<int> input_numbers;
        int num;
        while (iss >> num) {
            input_numbers.push_back(num);
        }
        
        istringstream oss(actual_output);
        vector<int> output_numbers;
        while (oss >> num) {
            output_numbers.push_back(num);
        }
        
        bool all_found = true;
        for (int input_num : input_numbers) {
            if (find(output_numbers.begin(), output_numbers.end(), input_num) == output_numbers.end()) {
                all_found = false;
                break;
            }
        }
        
        if (all_found) {
            cout << "{\\"status\\": \\"ACCEPTED\\", \\"score\\": 100, \\"message\\": \\"输出正确\\"}" << endl;
        } else {
            cout << "{\\"status\\": \\"WRONG_ANSWER\\", \\"score\\": 0, \\"message\\": \\"输出错误\\"}" << endl;
        }
        
    } catch (exception& e) {
        cout << "{\\"status\\": \\"SPJ_ERROR\\", \\"score\\": 0, \\"message\\": \\"SPJ脚本执行错误\\"}" << endl;
    }
    
    return 0;
}'''
    
    def create_problem(self, session: requests.Session, problem_id: str, judge_mode: str = "standard") -> Dict[str, Any]:
        """创建测试题目"""
        problem_data = {
            "id": problem_id,
            "title": f"SPJ测试题目 - {judge_mode}",
            "description": f"测试{judge_mode}模式的题目",
            "input_description": "输入两个整数",
            "output_description": "输出它们的和",
            "samples": [{"input": "1 2", "output": "3"}],
            "testcases": [{"input": "1 2", "output": "3"}],
            "constraints": "1 ≤ a, b ≤ 100",
            "hint": "简单加法",
            "source": "测试",
            "tags": ["测试", "SPJ"],
            "time_limit": 1.0,
            "memory_limit": 128,
            "author": "admin",
            "difficulty": "简单",
            "judge_mode": judge_mode
        }
        
        response = session.post(f"{BASE_URL}/api/problems/", json=problem_data)
        assert response.status_code == 200, f"创建题目失败: {response.text}"
        return response.json()
    
    def test_1_judge_mode_display(self, admin_session, spj_problem_id):
        """测试1: 后台管理界面需支持设置和显示judge_mode字段"""
        print("\n=== 测试1: judge_mode字段设置和显示 ===")
        
        # 创建标准模式题目
        standard_problem = self.create_problem(admin_session, f"{spj_problem_id}_standard", "standard")
        assert standard_problem["data"]["judge_mode"] == "standard"
        print("✅ 标准模式题目创建成功")
        
        # 创建SPJ模式题目
        spj_problem = self.create_problem(admin_session, f"{spj_problem_id}_spj", "spj")
        assert spj_problem["data"]["judge_mode"] == "spj"
        print("✅ SPJ模式题目创建成功")
        
        # 查询题目详情，验证judge_mode字段
        response = admin_session.get(f"{BASE_URL}/api/problems/{spj_problem_id}_spj")
        assert response.status_code == 200
        problem_data = response.json()["data"]
        assert "judge_mode" in problem_data
        assert problem_data["judge_mode"] == "spj"
        print("✅ judge_mode字段正确显示")
        
        # 清理
        admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}_standard")
        admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}_spj")
    
    def test_2_admin_spj_management(self, admin_session, spj_problem_id, python_spj_script, cpp_spj_script):
        """测试2: 管理员可以上传、更新、删除题目的SPJ脚本"""
        print("\n=== 测试2: 管理员SPJ脚本管理 ===")
        
        # 创建SPJ模式题目
        self.create_problem(admin_session, spj_problem_id, "spj")
        
        # 2.1 上传Python SPJ脚本
        print("2.1 上传Python SPJ脚本...")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200, f"上传Python SPJ失败: {response.text}"
        print("✅ Python SPJ脚本上传成功")
        
        # 验证题目状态
        response = admin_session.get(f"{BASE_URL}/api/problems/{spj_problem_id}")
        assert response.status_code == 200
        problem_data = response.json()["data"]
        assert problem_data["has_spj"] == True
        print("✅ 题目状态正确显示有SPJ")
        
        # 2.2 更新为C++ SPJ脚本
        print("2.2 更新为C++ SPJ脚本...")
        files = {"file": ("spj_script.cpp", cpp_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200, f"更新C++ SPJ失败: {response.text}"
        print("✅ C++ SPJ脚本更新成功")
        
        # 2.3 删除SPJ脚本
        print("2.3 删除SPJ脚本...")
        response = admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}/spj")
        assert response.status_code == 200, f"删除SPJ失败: {response.text}"
        print("✅ SPJ脚本删除成功")
        
        # 验证题目状态
        response = admin_session.get(f"{BASE_URL}/api/problems/{spj_problem_id}")
        assert response.status_code == 200
        problem_data = response.json()["data"]
        assert problem_data["has_spj"] == False
        print("✅ 题目状态正确显示无SPJ")
        
        # 清理
        admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}")
    
    def test_3_user_permission_denied(self, user_session, spj_problem_id, python_spj_script):
        """测试3: 普通用户无权上传/修改SPJ"""
        print("\n=== 测试3: 普通用户权限控制 ===")
        
        # 创建SPJ模式题目
        self.create_problem(user_session, spj_problem_id, "spj")
        
        # 尝试上传SPJ脚本
        print("3.1 普通用户尝试上传SPJ脚本...")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = user_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 403, "普通用户应该无法上传SPJ"
        print("✅ 正确拒绝普通用户上传SPJ")
        
        # 尝试删除SPJ脚本
        print("3.2 普通用户尝试删除SPJ脚本...")
        response = user_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}/spj")
        assert response.status_code == 403, "普通用户应该无法删除SPJ"
        print("✅ 正确拒绝普通用户删除SPJ")
        
        # 清理
        user_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}")
    
    def test_4_spj_evaluation(self, admin_session, user_session, spj_problem_id, python_spj_script):
        """测试4: 评测时可以正确调用SPJ脚本运行评测"""
        print("\n=== 测试4: SPJ脚本评测 ===")
        
        # 管理员创建SPJ题目并上传脚本
        self.create_problem(admin_session, spj_problem_id, "spj")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        
        # 4.1 提交正确代码（应该AC）
        print("4.1 提交正确代码...")
        correct_code = "a, b = map(int, input().split())\nprint(a + b)"
        submission_data = {
            "problem_id": spj_problem_id,
            "language": "python",
            "code": correct_code
        }
        
        response = user_session.post(f"{BASE_URL}/api/submissions/", json=submission_data)
        assert response.status_code == 200
        submission_id = response.json()["data"]["submission_id"]
        print(f"✅ 正确代码提交成功，ID: {submission_id}")
        
        # 等待评测
        time.sleep(3)
        
        # 查询结果
        response = user_session.get(f"{BASE_URL}/api/submissions/{submission_id}")
        assert response.status_code == 200
        result = response.json()["data"]
        print(f"正确代码评测结果: {result['status']}, 得分: {result['score']}")
        
        # 4.2 提交错误代码（应该WA）
        print("4.2 提交错误代码...")
        wrong_code = "a, b = map(int, input().split())\nprint(a - b)"  # 减法而不是加法
        submission_data["code"] = wrong_code
        
        response = user_session.post(f"{BASE_URL}/api/submissions/", json=submission_data)
        assert response.status_code == 200
        wrong_submission_id = response.json()["data"]["submission_id"]
        print(f"✅ 错误代码提交成功，ID: {wrong_submission_id}")
        
        # 等待评测
        time.sleep(3)
        
        # 查询结果
        response = user_session.get(f"{BASE_URL}/api/submissions/{wrong_submission_id}")
        assert response.status_code == 200
        wrong_result = response.json()["data"]
        print(f"错误代码评测结果: {wrong_result['status']}, 得分: {wrong_result['score']}")
        
        # 验证结果
        assert result["score"] > 0, "正确代码应该得分"
        assert wrong_result["score"] == 0, "错误代码应该得0分"
        print("✅ SPJ评测结果正确")
        
        # 清理
        admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}")
    
    def test_5_security_validation(self, admin_session, spj_problem_id):
        """测试5: 系统能校验上传脚本的文件类型、内容安全"""
        print("\n=== 测试5: 安全验证 ===")
        
        # 创建SPJ模式题目
        self.create_problem(admin_session, spj_problem_id, "spj")
        
        # 5.1 测试不支持的文件类型
        print("5.1 测试不支持的文件类型...")
        js_script = 'console.log("test");'
        files = {"file": ("spj_script.js", js_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 400, "应该拒绝.js文件"
        print("✅ 正确拒绝.js文件")
        
        # 5.2 测试危险脚本内容
        print("5.2 测试危险脚本内容...")
        dangerous_scripts = [
            'import os; os.system("rm -rf /")',
            'eval("print(1)")',
            'exec("print(1)")',
            'subprocess.call(["rm", "-rf", "/"])',
            'subprocess.run(["rm", "-rf", "/"])'
        ]
        
        for i, dangerous_script in enumerate(dangerous_scripts):
            files = {"file": (f"dangerous_{i}.py", dangerous_script.encode('utf-8'), "text/plain")}
            response = admin_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj", files=files)
            assert response.status_code == 400, f"应该拒绝危险脚本 {i+1}"
            print(f"✅ 正确拒绝危险脚本 {i+1}")
        
        # 5.3 测试正常脚本（应该通过）
        print("5.3 测试正常脚本...")
        normal_script = '''#!/usr/bin/env python3
import json
import sys

def main():
    data = json.loads(sys.stdin.read())
    print(json.dumps({"status": "ACCEPTED", "score": 100}))

if __name__ == "__main__":
    main()
'''
        files = {"file": ("normal.py", normal_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200, "正常脚本应该通过"
        print("✅ 正常脚本通过验证")
        
        # 清理
        admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}/spj")
        admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}")
    
    def test_6_spj_test_interface(self, admin_session, spj_problem_id, python_spj_script):
        """测试6: SPJ脚本测试接口"""
        print("\n=== 测试6: SPJ脚本测试接口 ===")
        
        # 创建SPJ题目并上传脚本
        self.create_problem(admin_session, spj_problem_id, "spj")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        
        # 测试SPJ脚本
        print("6.1 测试SPJ脚本执行...")
        test_data = {
            "input_data": "1 2",
            "expected_output": "3",
            "actual_output": "3"
        }
        
        response = admin_session.post(f"{BASE_URL}/api/problems/{spj_problem_id}/spj/test", data=test_data)
        assert response.status_code == 200
        test_result = response.json()["data"]
        print(f"SPJ测试结果: {test_result}")
        
        # 验证测试结果
        assert test_result["status"] == "ACCEPTED"
        assert test_result["score"] == 100
        print("✅ SPJ脚本测试接口正常")
        
        # 清理
        admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}/spj")
        admin_session.delete(f"{BASE_URL}/api/problems/{spj_problem_id}")


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v"]) 